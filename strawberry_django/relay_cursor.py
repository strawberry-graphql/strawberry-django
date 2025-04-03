import dataclasses
import json
from json import JSONDecodeError
from typing import ClassVar, Self, Optional, Any, NamedTuple, cast

import strawberry
from django.db import models, DEFAULT_DB_ALIAS
from django.db.models import QuerySet, Q, OrderBy, F, Window
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import RowNumber
from strawberry import relay, Info
from strawberry.relay import from_base64, to_base64, NodeType, PageInfo
from strawberry.relay.types import NodeIterableType
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
    # TODO: fall back to default order
    return qs.query.order_by


class OrderingDescriptor(NamedTuple):
    field: str
    descending: bool
    order_by: Optional[OrderBy]
    output_field: models.Field | None = None

    @property
    def nulls_first(self) -> bool:
        return self.order_by is not None and self.order_by.nulls_first

    def compare(self, value, before: bool) -> Q | None:
        if value is None:
            if self.nulls_first ^ before:
                return Q((f'{self.field}__isnull', False))
            else:
                return None
        else:
            lookup = 'lt' if before ^ self.descending else 'gt'
            return Q((f'{self.field}{LOOKUP_SEP}{lookup}', value))

    def get_eq(self, value) -> Q:
        if value is None:
            return Q((f'{self.field}__isnull', True))
        else:
            return Q((f'{self.field}__exact', value))

    def reverse(self):
        if self.order_by is None:
            return OrderBy(F(self.field), not self.descending)
        else:
            return OrderBy(
                self.order_by.expression,
                not self.order_by.descending,
                self.order_by.nulls_first,
                self.order_by.nulls_last,
            )


def annotate_ordering_fields(qs: QuerySet) -> tuple[QuerySet, list[OrderingDescriptor], list[OrderBy]]:
    annotations = {}
    descriptors = []
    index = 0
    new_order_by = []
    order_bys = _get_order_by(qs)
    for order_by in order_bys:
        if order_by == '?':
            raise ValueError('Random ordering cannot be combined with cursor pagination')
        if isinstance(order_by, str):
            if order_by[0] == '-':
                field_name = order_by[1:]
                descending = True
            else:
                field_name = order_by
                descending = False

            if field_name in qs.query.annotations:
                # if it's an annotation, make sure it is selected and not just an alias
                # Otherwise, it's a field and we don't need to annotate it
                annotations[field_name] = F(field_name)
            descriptors.append(OrderingDescriptor(field_name, descending, None))
            new_order_by.append(order_by)
        else:
            dynamic_field = f'_strawberry_order_field_{index}'
            annotations[dynamic_field] = order_by.expression
            new_order_by.append(
                OrderBy(F(dynamic_field), order_by.descending, order_by.nulls_first, order_by.nulls_last)
            )
            descriptors.append(OrderingDescriptor(dynamic_field, order_by.descending, order_by))
    return qs.annotate(**annotations).order_by(*new_order_by), descriptors, order_bys


def extract_cursor_values(descriptors: list[OrderingDescriptor], obj: models.Model) -> list:
    return [
        getattr(obj, descriptor.field)
        for descriptor in descriptors
    ]


def build_tuple_compare(descriptors: list[OrderingDescriptor], cursor_values: list, before: bool) -> Q:
    current = None
    for descriptor, field_value in zip(reversed(descriptors), reversed(cursor_values)):
        lt = descriptor.compare(field_value, before)
        if current is None:
            current = lt
        else:
            eq = descriptor.get_eq(field_value)
            current = lt | (eq & current) if lt is not None else eq & current
    return current if current is not None else Q()


@dataclasses.dataclass
class OrderedCollectionCursor:
    PREFIX: ClassVar[str] = 'orderedcursor'

    field_values: list[str]

    @classmethod
    def from_model(cls, model: models.Model, descriptors: list[OrderingDescriptor]) -> Self:
        values = []
        for descriptor in descriptors:
            values.append(str(getattr(model, descriptor.field)))  # type: ignore
        return OrderedCollectionCursor(field_values=values)

    @classmethod
    def from_cursor(cls, cursor: str) -> Self:
        type_, values_json = from_base64(cursor)
        if type_ != cls.PREFIX:
            raise ValueError('Invalid Cursor')
        try:
            decoded_values = json.loads(values_json)
        except JSONDecodeError as e:
            raise ValueError('Invalid cursor') from e
        if not isinstance(decoded_values, list):
            raise ValueError('Invalid cursor')
        if any(not isinstance(v, str) for v in decoded_values):
            raise ValueError('Invalid cursor')
        return OrderedCollectionCursor(decoded_values)

    def to_cursor(self) -> str:
        return to_base64(self.PREFIX, json.dumps(self.field_values))


@strawberry.type(name="CursorEdge", description="An edge in a connection.")
class DjangoCursorEdge(relay.Edge[relay.NodeType]):

    @classmethod
    def resolve_edge(cls, node: NodeType, *, cursor: OrderedCollectionCursor = None) -> Self:
        return cls(cursor=cursor.to_cursor(), node=node)


@strawberry.type(name="CursorConnection", description="A connection to a list of items.")
class DjangoCursorConnection(relay.Connection[relay.NodeType]):

    edges: list[DjangoCursorEdge[NodeType]] = strawberry.field(
        description="Contains the nodes in this connection"
    )

    @classmethod
    def resolve_connection(cls, nodes: NodeIterableType[NodeType], *, info: Info, before: Optional[str] = None,
                           after: Optional[str] = None, first: Optional[int] = None, last: Optional[int] = None,
                           max_results: Optional[int] = None, **kwargs: Any) -> AwaitableOrValue[Self]:
        if not isinstance(nodes, QuerySet):
            raise TypeError('DjangoCursorConnection requires a QuerySet')

        max_results = (
            max_results
            if max_results is not None
            else info.schema.config.relay_max_results
        )

        nodes, ordering_descriptors, original_order_by = annotate_ordering_fields(nodes)

        if after:
            after_cursor = OrderedCollectionCursor.from_cursor(after)
            nodes = nodes.filter(build_tuple_compare(
                ordering_descriptors, after_cursor.field_values, False
            ))
        if before:
            before_cursor = OrderedCollectionCursor.from_cursor(before)
            nodes = nodes.filter(build_tuple_compare(
                ordering_descriptors, before_cursor.field_values, True
            ))

        iterate_backwards = False
        slice_: slice | None = None
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
            current_order = [
                expr
                for expr, _ in nodes.query.get_compiler(
                    using=nodes._db or DEFAULT_DB_ALIAS  # type: ignore
                ).get_order_by()
            ]
            nodes = nodes.reverse().annotate(
                _strawberry_row_number_fwd=Window(
                    RowNumber(),
                    order_by=current_order,
                ),
            ).filter(
                _strawberry_row_number_fwd__lte=first,
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
            slice_ = slice(first)
        elif last is not None:
            # when using last, optimize by reversing the QuerySet ord100010001000ering in the DB,
            # then slicing from the end and iterating in reverse10001000
            if last < 0:
                raise ValueError("Argument 'last' must be a non-negative integer.")
            if last > max_results:
                raise ValueError(
                    f"Argument 'last' cannot be higher than {max_results}."
                )
            slice_ = slice(last)
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

        edges = [
            edge_class.resolve_edge(
                cls.resolve_node(v, info=info, **kwargs),
                cursor=OrderedCollectionCursor.from_model(v, ordering_descriptors)
            )
            for v in (reversed(nodes) if iterate_backwards else nodes)
        ]

        return cls(
            edges=edges,
            page_info=PageInfo(
                has_next_page=False,
                has_previous_page=False,
                start_cursor='',
                end_cursor='',
            )
        )
