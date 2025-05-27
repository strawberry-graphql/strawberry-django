import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, ClassVar, Optional, cast

import strawberry
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS, models
from django.db.models import Expression, F, OrderBy, Q, QuerySet, Value, Window
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Col
from django.db.models.functions import RowNumber
from django.db.models.sql.datastructures import BaseTable
from strawberry import Info, relay
from strawberry.relay import NodeType, PageInfo, from_base64
from strawberry.relay.types import NodeIterableType
from strawberry.relay.utils import should_resolve_list_connection_edges
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.utils.await_maybe import AwaitableOrValue
from strawberry.utils.inspect import in_async_context
from typing_extensions import Self

from strawberry_django.pagination import apply_window_pagination, get_total_count
from strawberry_django.queryset import get_queryset_config
from strawberry_django.resolvers import django_resolver


def _get_order_by(qs: QuerySet) -> list[OrderBy]:
    return [
        expr
        for expr, _ in qs.query.get_compiler(
            using=qs._db or DEFAULT_DB_ALIAS  # type: ignore
        ).get_order_by()
    ]


@dataclass
class OrderingDescriptor:
    attname: str
    order_by: OrderBy
    # we have to assume everything is nullable by default
    maybe_null: bool = True

    def get_comparator(self, value: Any, before: bool) -> Optional[Q]:
        if value is None:
            # 1. When nulls are first:
            #    1.1 there is nothing before "null"
            #    1.2 after "null" comes everything non-null
            # 2. When nulls are last:
            #    2.1 there is nothing after "null"
            #    2.2 before "null" comes everything non-null
            # => 1.1 and 2.1 require no checks
            # => 1.2 and 2.2 require an "is not null" check
            if bool(self.order_by.nulls_first) ^ before:
                return Q((f"{self.attname}{LOOKUP_SEP}isnull", False))
            return None
        lookup = "lt" if before ^ self.order_by.descending else "gt"
        cmp = Q((f"{self.attname}{LOOKUP_SEP}{lookup}", value))

        if self.maybe_null and bool(self.order_by.nulls_first) == before:
            # if nulls are first, "before any value" can also mean "is null"
            # if nulls are last, "after any value" can also mean "is null"
            cmp |= Q((f"{self.attname}{LOOKUP_SEP}isnull", True))
        return cmp

    def get_eq(self, value) -> Q:
        if value is None:
            return Q((f"{self.attname}{LOOKUP_SEP}isnull", True))
        return Q((f"{self.attname}{LOOKUP_SEP}exact", value))


def annotate_ordering_fields(
    qs: QuerySet,
) -> tuple[QuerySet, list[OrderingDescriptor], list[OrderBy]]:
    annotations = {}
    descriptors = []
    new_defer = None
    new_only = None
    order_bys = _get_order_by(qs)
    pk_in_order = False
    for index, order_by in enumerate(order_bys):
        if isinstance(order_by.expression, Col) and isinstance(
            # Col.alias is missing from django-types
            qs.query.alias_map[order_by.expression.alias],  # type: ignore
            BaseTable,
        ):
            field_name = order_by.expression.field.name
            # if it's a field in the base table, just make sure it is not deferred (e.g. by the optimizer)
            existing, defer = qs.query.deferred_loading
            if defer and field_name in existing:
                # Query is in "defer fields" mode and our field is being deferred
                if new_defer is None:
                    new_defer = set(existing)
                new_defer.discard(field_name)
            elif not defer and field_name not in existing:
                # Query is in "only these fields" mode and our field is not in the set of fields
                if new_only is None:
                    new_only = set(existing)
                new_only.add(field_name)
            descriptors.append(
                OrderingDescriptor(
                    order_by.expression.field.attname,
                    order_by,
                    maybe_null=order_by.expression.field.null,
                )
            )
            if order_by.expression.field.primary_key:
                pk_in_order = True
        else:
            dynamic_field = f"_strawberry_order_field_{index}"
            annotations[dynamic_field] = order_by.expression
            descriptors.append(OrderingDescriptor(dynamic_field, order_by))

    if new_defer is not None:
        # defer is additive, so clear it first
        qs = qs.defer(None).defer(*new_defer)
    elif new_only is not None:
        # only overwrites
        qs = qs.only(*new_only)

    if not pk_in_order:
        # Ensure we always have a clearly defined order by ordering by pk if it isn't in the order already
        # We cannot use QuerySet.order_by, because it validates the order expressions again,
        # but we're operating on the OrderBy expressions which have already been resolved by the compiler
        # In case the user has previously ordered by an aggregate like so:
        # qs.annotate(_c=Count("foo")).order_by("_c")  # noqa: ERA001
        # then the OrderBy we get here would trigger a ValidationError by QuerySet.order_by.
        # But we only want to append to the existing order (and the existing order must be valid already)
        # So this is safe.
        pk_order = F("pk").resolve_expression(qs.query).asc()
        order_bys.append(pk_order)
        descriptors.append(OrderingDescriptor("pk", pk_order, maybe_null=False))
        qs = qs._chain()  # type: ignore
        qs.query.order_by += (pk_order,)
    return qs.annotate(**annotations), descriptors, order_bys


def build_tuple_compare(
    descriptors: list[OrderingDescriptor],
    cursor_values: list[Optional[str]],
    before: bool,
) -> Q:
    current = None
    for descriptor, field_value in zip(reversed(descriptors), reversed(cursor_values)):
        if field_value is None:
            value_expr = None
        else:
            output_field = descriptor.order_by.expression.output_field
            value_expr = Value(field_value, output_field=output_field)
        cmp = descriptor.get_comparator(value_expr, before)
        if current is None:
            current = cmp
        else:
            eq = descriptor.get_eq(value_expr)
            current = cmp | (eq & current) if cmp is not None else eq & current
    return current if current is not None else Q()


class AttrHelper:
    pass


def _extract_expression_value(
    model: models.Model, expr: Expression, attname: str
) -> Optional[str]:
    output_field = expr.output_field
    # Unfortunately Field.value_to_string operates on the object, not a direct value
    # So we have to potentially construct a fake object
    # If the output field's attname doesn't match, we have to construct a fake object
    # Additionally, the output field may not have an attname at all
    # if expressions are used
    field_attname = getattr(output_field, "attname", None)
    if not field_attname:
        # If the field doesn't have an attname, it's a dynamically constructed field,
        # for the purposes of output_field in an expression. Just set its attname, it doesn't hurt anything
        output_field.attname = field_attname = attname
    obj: Any
    if field_attname != attname:
        obj = AttrHelper()
        setattr(obj, output_field.attname, getattr(model, attname))
    else:
        obj = model
    value = output_field.value_from_object(obj)
    if value is None:
        return None
    # value_to_string is missing from django-types
    return output_field.value_to_string(obj)  # type: ignore


def apply_cursor_pagination(
    qs: QuerySet,
    *,
    related_field_id: Optional[str] = None,
    info: Info,
    before: Optional[str],
    after: Optional[str],
    first: Optional[int],
    last: Optional[int],
    max_results: Optional[int],
) -> tuple[QuerySet, list[OrderingDescriptor]]:
    max_results = (
        max_results if max_results is not None else info.schema.config.relay_max_results
    )

    qs, ordering_descriptors, original_order_by = annotate_ordering_fields(qs)
    if after:
        after_cursor = OrderedCollectionCursor.from_cursor(after, ordering_descriptors)
        qs = qs.filter(
            build_tuple_compare(ordering_descriptors, after_cursor.field_values, False)
        )
    if before:
        before_cursor = OrderedCollectionCursor.from_cursor(
            before, ordering_descriptors
        )
        qs = qs.filter(
            build_tuple_compare(ordering_descriptors, before_cursor.field_values, True)
        )

    slice_: Optional[slice] = None
    if first is not None and last is not None:
        if last > max_results:
            raise ValueError(f"Argument 'last' cannot be higher than {max_results}.")
        # if first and last are given, we have to
        # - reverse the order in the DB so we can use slicing to apply [:last],
        #   otherwise we would have to know the total count to apply slicing from the end
        # - We still need to apply forward-direction [:first] slicing, and according to the Relay spec,
        #   it shall happen before [:last] slicing. To do this, we use a window function with a RowNumber ordered
        #   in the original direction, which is opposite the actual query order.
        #   This query is likely not very efficient, but using last _and_ first together is discouraged by the
        #   spec anyway
        qs = (
            qs.reverse()
            .annotate(
                _strawberry_row_number_fwd=Window(
                    RowNumber(),
                    order_by=original_order_by,
                ),
            )
            .filter(
                _strawberry_row_number_fwd__lte=first + 1,
            )
        )
        # we're overfetching by two, in both directions
        slice_ = slice(last + 2)
    elif first is not None:
        if first < 0:
            raise ValueError("Argument 'first' must be a non-negative integer.")
        if first > max_results:
            raise ValueError(f"Argument 'first' cannot be higher than {max_results}.")
        slice_ = slice(first + 1)
    elif last is not None:
        # when using last, optimize by reversing the QuerySet ordering in the DB,
        # then slicing from the end (which is now the start in QuerySet ordering)
        # and then iterating the results in reverse to restore the original order
        if last < 0:
            raise ValueError("Argument 'last' must be a non-negative integer.")
        if last > max_results:
            raise ValueError(f"Argument 'last' cannot be higher than {max_results}.")
        slice_ = slice(last + 1)
        qs = qs.reverse()
    if related_field_id is not None:
        # we always apply window pagination for nested connections,
        # because we want its total count annotation
        offset = slice_.start or 0 if slice_ is not None else 0
        qs = apply_window_pagination(
            qs,
            related_field_id=related_field_id,
            offset=offset,
            limit=slice_.stop - offset if slice_ is not None else None,
        )
    elif slice_ is not None:
        qs = qs[slice_]

    get_queryset_config(qs).ordering_descriptors = ordering_descriptors

    return qs, ordering_descriptors


@dataclass
class OrderedCollectionCursor:
    field_values: list[Any]

    @classmethod
    def from_model(
        cls, model: models.Model, descriptors: list[OrderingDescriptor]
    ) -> Self:
        values = [
            _extract_expression_value(
                model, descriptor.order_by.expression, descriptor.attname
            )
            for descriptor in descriptors
        ]
        return cls(field_values=values)

    @classmethod
    def from_cursor(cls, cursor: str, descriptors: list[OrderingDescriptor]) -> Self:
        type_, values_json = from_base64(cursor)
        if type_ != DjangoCursorEdge.CURSOR_PREFIX:
            raise ValueError("Invalid cursor")
        try:
            string_values = json.loads(values_json)
        except JSONDecodeError as e:
            raise ValueError("Invalid cursor") from e
        if (
            not isinstance(string_values, list)
            or len(string_values) != len(descriptors)
            or any(not (v is None or isinstance(v, str)) for v in string_values)
        ):
            raise ValueError("Invalid cursor")

        try:
            decoded_values = [
                d.order_by.expression.output_field.to_python(v)
                for d, v in zip(descriptors, string_values)
            ]
        except ValidationError as e:
            raise ValueError("Invalid cursor") from e

        return cls(decoded_values)

    def __str__(self):
        return json.dumps(self.field_values, separators=(",", ":"))


@strawberry.type(name="CursorEdge", description="An edge in a connection.")
class DjangoCursorEdge(relay.Edge[relay.NodeType]):
    CURSOR_PREFIX: ClassVar[str] = "orderedcursor"


@strawberry.type(
    name="CursorConnection", description="A connection to a list of items."
)
class DjangoCursorConnection(relay.Connection[relay.NodeType]):
    total_count_qs: strawberry.Private[Optional[QuerySet]] = None
    edges: list[DjangoCursorEdge[NodeType]] = strawberry.field(  # type: ignore
        description="Contains the nodes in this connection"
    )

    @strawberry.field(description="Total quantity of existing nodes.")
    @django_resolver
    def total_count(self) -> int:
        assert self.total_count_qs is not None

        return get_total_count(self.total_count_qs)

    @classmethod
    def resolve_connection(
        cls,
        nodes: NodeIterableType[NodeType],
        *,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        max_results: Optional[int] = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        from strawberry_django.optimizer import is_optimized_by_prefetching

        if not isinstance(nodes, QuerySet):
            raise TypeError("DjangoCursorConnection requires a QuerySet")
        total_count_qs: QuerySet = nodes
        qs: QuerySet
        if not is_optimized_by_prefetching(nodes):
            qs, ordering_descriptors = apply_cursor_pagination(
                nodes,
                info=info,
                before=before,
                after=after,
                first=first,
                last=last,
                max_results=max_results,
            )
        else:
            qs = nodes
            ordering_descriptors = get_queryset_config(qs).ordering_descriptors
            assert ordering_descriptors is not None

        type_def = get_object_definition(cls)
        assert type_def
        field_def = type_def.get_field("edges")
        assert field_def

        field = field_def.resolve_type(type_definition=type_def)
        while isinstance(field, StrawberryContainer):
            field = field.of_type

        edge_class = cast("DjangoCursorEdge[NodeType]", field)

        if not should_resolve_list_connection_edges(info):
            return cls(
                edges=[],
                total_count_qs=total_count_qs,
                page_info=PageInfo(
                    start_cursor=None,
                    end_cursor=None,
                    has_previous_page=False,
                    has_next_page=False,
                ),
            )

        def finish_resolving():
            nonlocal qs
            has_previous_page = has_next_page = False

            results = list(qs)

            if first is not None:
                if last is None:
                    has_next_page = len(results) > first
                    results = results[:first]
                # we're paginating forwards _and_ backwards
                # remove the (potentially) overfetched row in the forwards direction first
                elif (
                    results
                    and getattr(results[0], "_strawberry_row_number_fwd", 0) > first
                ):
                    has_next_page = True
                    results = results[1:]

            if last is not None:
                has_previous_page = len(results) > last
                results = results[:last]

            it = reversed(results) if last is not None else results

            edges = [
                edge_class.resolve_edge(
                    cls.resolve_node(v, info=info, **kwargs),
                    cursor=OrderedCollectionCursor.from_model(v, ordering_descriptors),
                )
                for v in it
            ]

            return cls(
                edges=edges,
                total_count_qs=total_count_qs,
                page_info=PageInfo(
                    start_cursor=edges[0].cursor if edges else None,
                    end_cursor=edges[-1].cursor if edges else None,
                    has_previous_page=has_previous_page,
                    has_next_page=has_next_page,
                ),
            )

        if in_async_context() and qs._result_cache is None:  # type: ignore
            return sync_to_async(finish_resolving)()
        return finish_resolving()
