import dataclasses
import json
from json import JSONDecodeError
from typing import ClassVar, Self, Optional, Any, NamedTuple, cast

import strawberry
from django.core.exceptions import ValidationError
from django.db import models, DEFAULT_DB_ALIAS, connections
from django.db.models import QuerySet, Q, OrderBy, Window, Func, Value
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import BaseExpression
from django.db.models.functions import RowNumber
from django.db.models.lookups import LessThan, GreaterThan
from strawberry import relay, Info
from strawberry.relay import from_base64, to_base64, NodeType, PageInfo
from strawberry.relay.types import NodeIterableType
from strawberry.relay.utils import should_resolve_list_connection_edges
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.utils.await_maybe import AwaitableOrValue


def _get_order_by(qs: QuerySet) -> list[OrderBy]:
    order_by = [
        expr
        for expr, _ in qs.query.get_compiler(
            using=qs._db or DEFAULT_DB_ALIAS  # type: ignore
        ).get_order_by()
    ]
    return order_by


class OrderingDescriptor(NamedTuple):
    alias: str
    order_by: OrderBy

    def get_comparator(self, value, before: bool) -> Q | None:
        if value is None:
            if bool(self.order_by.nulls_first) ^ before:
                return Q((f"{self.alias}__isnull", False))
            else:
                return None
        else:
            lookup = "lt" if before ^ self.order_by.descending else "gt"
            return Q((f"{self.alias}{LOOKUP_SEP}{lookup}", value))

    def get_eq(self, value) -> Q:
        if value is None:
            return Q((f"{self.alias}__isnull", True))
        else:
            return Q((f"{self.alias}__exact", value))


def annotate_ordering_fields(
    qs: QuerySet,
) -> tuple[QuerySet, list[OrderingDescriptor], list[OrderBy]]:
    annotations = {}
    descriptors = []
    order_bys = _get_order_by(qs)
    for index, order_by in enumerate(order_bys):
        # TODO: Could optimize this for ordering by plain fields
        # Those don't need annotations, but we need to make sure they are not deferred by the optimizer
        dynamic_field = f"_strawberry_order_field_{index}"
        annotations[dynamic_field] = order_by.expression
        descriptors.append(OrderingDescriptor(dynamic_field, order_by))
    return qs.annotate(**annotations), descriptors, order_bys


def extract_cursor_values(
    descriptors: list[OrderingDescriptor], obj: models.Model
) -> list:
    return [getattr(obj, descriptor.alias) for descriptor in descriptors]


_tuple_constructor_func = {
    "sqlite": "",
    "postgresql": "",
    "mysql": "",
}


def build_tuple_compare(
    qs: QuerySet,
    descriptors: list[OrderingDescriptor],
    cursor_values: list,
    before: bool,
) -> Q:
    if len(descriptors) > 1:
        # if possible, use more efficient tuple comparison
        # i.e. (foo, bar, baz) < (1, 2, 3)
        db = qs._db or DEFAULT_DB_ALIAS
        connection = connections[db]
        tuple_func = _tuple_constructor_func.get(connection.vendor)
        if tuple_func is not None:
            lhs_args = []
            rhs_args = []
            for descriptor, value in zip(descriptors, cursor_values):
                order_by_expression = descriptor.order_by.expression
                lhs_args.append(order_by_expression)
                rhs_args.append(
                    Value(value, output_field=order_by_expression.output_field)
                )

            # lhs and rhs get a dummy (but equal) output_field, because Django does not understand tuple types
            lhs = Func(*lhs_args, function=tuple_func, output_field=models.TextField())
            rhs = Func(*rhs_args, function=tuple_func, output_field=models.TextField())
            cmp = LessThan(lhs, rhs) if before else GreaterThan(lhs, rhs)
            return Q(cmp)
    current = None
    for descriptor, field_value in zip(reversed(descriptors), reversed(cursor_values)):
        value_expr = Value(
            field_value, output_field=descriptor.order_by.expression.output_field
        )
        lt = descriptor.get_comparator(value_expr, before)
        if current is None:
            current = lt
        else:
            eq = descriptor.get_eq(value_expr)
            current = lt | (eq & current) if lt is not None else eq & current
    return current if current is not None else Q()


class AttrHelper:
    pass


def _extract_expression_value(model: models.Model, expr: BaseExpression, attname: str) -> str:
    output_field = expr.output_field
    # If the output field's attname doesn't match, we have to construct a fake object
    if output_field.attname != attname:
        obj = AttrHelper()
        setattr(obj, output_field.attname, getattr(model, attname))
    else:
        obj = model
    return output_field.value_to_string(obj)


@dataclasses.dataclass
class OrderedCollectionCursor:
    PREFIX: ClassVar[str] = "orderedcursor"

    field_values: list[str]

    @classmethod
    def from_model(
        cls, model: models.Model, descriptors: list[OrderingDescriptor]
    ) -> Self:
        values = [
            _extract_expression_value(model, descriptor.order_by.expression, descriptor.alias)
            for descriptor in descriptors
        ]
        return OrderedCollectionCursor(field_values=values)

    @classmethod
    def from_cursor(cls, cursor: str, descriptors: list[OrderingDescriptor]) -> Self:
        type_, values_json = from_base64(cursor)
        if type_ != cls.PREFIX:
            raise ValueError("Invalid Cursor")
        try:
            string_values = json.loads(values_json)
        except JSONDecodeError as e:
            raise ValueError("Invalid cursor") from e
        if (
            not isinstance(string_values, list)
            or len(string_values) != len(descriptors)
            or any(not isinstance(v, str) for v in string_values)
        ):
            raise ValueError("Invalid cursor")

        try:
            decoded_values = [
                d.order_by.expression.output_field.to_python(v)
                for d, v in zip(descriptors, string_values)
            ]
        except ValidationError:
            raise ValueError("Invalid cursor")

        return OrderedCollectionCursor(decoded_values)

    def to_cursor(self) -> str:
        return to_base64(self.PREFIX, json.dumps(self.field_values))


@strawberry.type(name="CursorEdge", description="An edge in a connection.")
class DjangoCursorEdge(relay.Edge[relay.NodeType]):
    @classmethod
    def resolve_edge(
        cls, node: NodeType, *, cursor: OrderedCollectionCursor = None
    ) -> Self:
        return cls(cursor=cursor.to_cursor(), node=node)


@strawberry.type(
    name="CursorConnection", description="A connection to a list of items."
)
class DjangoCursorConnection(relay.Connection[relay.NodeType]):
    edges: list[DjangoCursorEdge[NodeType]] = strawberry.field(
        description="Contains the nodes in this connection"
    )

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
        if not isinstance(nodes, QuerySet):
            raise TypeError("DjangoCursorConnection requires a QuerySet")

        max_results = (
            max_results
            if max_results is not None
            else info.schema.config.relay_max_results
        )

        nodes, ordering_descriptors, original_order_by = annotate_ordering_fields(nodes)

        if after:
            after_cursor = OrderedCollectionCursor.from_cursor(
                after, ordering_descriptors
            )
            nodes = nodes.filter(
                build_tuple_compare(
                    nodes, ordering_descriptors, after_cursor.field_values, False
                )
            )
        if before:
            before_cursor = OrderedCollectionCursor.from_cursor(
                before, ordering_descriptors
            )
            nodes = nodes.filter(
                build_tuple_compare(
                    nodes, ordering_descriptors, before_cursor.field_values, True
                )
            )

        has_previous_page = has_next_page = False
        iterate_backwards = False
        slice_: slice | None = None
        real_limit: int | None = None
        if first is not None and last is not None:
            if last > max_results:
                raise ValueError(
                    f"Argument 'last' cannot be higher than {max_results}."
                )
            # if first and last are given, we have to
            # - reverse the order in the DB so we can use slicing to apply [:last],
            #   otherwise we would have to know the total count to apply slicing from the end
            # - We still need to apply forward-direction [:first] slicing, and according to the Relay spec,
            #   it shall happen before [:last] slicing. To do this, we use a window function with a RowNumber ordered
            #   in the original direction, which is opposite the actual query order.
            #   This query is likely not very efficient, but using last _and_ first together is discouraged by the
            #   spec anyway
            nodes = (
                nodes.reverse()
                .annotate(
                    _strawberry_row_number_fwd=Window(
                        RowNumber(),
                        order_by=original_order_by,
                    ),
                )
                .filter(
                    _strawberry_row_number_fwd__lte=first,
                )
            )
            slice_ = slice(last)
            iterate_backwards = True
        elif first is not None:
            if first < 0:
                raise ValueError("Argument 'first' must be a non-negative integer.")
            if first > max_results:
                raise ValueError(
                    f"Argument 'first' cannot be higher than {max_results}."
                )
            slice_ = slice(first + 1)
            real_limit = first
        elif last is not None:
            # when using last, optimize by reversing the QuerySet ordering in the DB,
            # then slicing from the end (which is now the start in QuerySet ordering)
            # and then iterating the results in reverse to restore the original order
            if last < 0:
                raise ValueError("Argument 'last' must be a non-negative integer.")
            if last > max_results:
                raise ValueError(
                    f"Argument 'last' cannot be higher than {max_results}."
                )
            slice_ = slice(last + 1)
            real_limit = last
            nodes = nodes.reverse()
            iterate_backwards = True
        if slice_ is not None:
            nodes = nodes[slice_]

        type_def = get_object_definition(cls)
        assert type_def
        field_def = type_def.get_field("edges")
        assert field_def

        field = field_def.resolve_type(type_definition=type_def)
        while isinstance(field, StrawberryContainer):
            field = field.of_type

        edge_class = cast(DjangoCursorEdge[NodeType], field)

        if not should_resolve_list_connection_edges(info):
            return cls(
                edges=[],
                page_info=PageInfo(
                    start_cursor=None,
                    end_cursor=None,
                    has_previous_page=False,
                    has_next_page=False,
                ),
            )

        if real_limit is not None:
            has_more = len(nodes) > real_limit
            if iterate_backwards:
                has_previous_page = has_more
            else:
                has_next_page = has_more
            nodes = nodes[:real_limit]

        if iterate_backwards:
            nodes = reversed(nodes)

        edges = [
            edge_class.resolve_edge(
                cls.resolve_node(v, info=info, **kwargs),
                cursor=OrderedCollectionCursor.from_model(v, ordering_descriptors),
            )
            for v in nodes
        ]

        return cls(
            edges=edges,
            page_info=PageInfo(
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
                has_previous_page=bool(has_previous_page),
                has_next_page=bool(has_next_page),
            ),
        )
