import dataclasses
import json
from json import JSONDecodeError
from typing import ClassVar, Self, Collection, Optional, Any, NamedTuple, cast

import strawberry
from django.db.models.constants import LOOKUP_SEP
from strawberry import relay, Info
from strawberry.relay.types import NodeIterableType
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.utils.await_maybe import AwaitableOrValue
from typing_extensions import Literal

from django.db import models
from django.db.models import QuerySet, Q, OrderBy, F
from strawberry.relay import from_base64, to_base64, NodeType, PageInfo

from strawberry_django.utils.inspect import get_model_fields


def _get_order_by(qs: QuerySet) -> list[str | OrderBy]:
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


def annotate_ordering_fields(qs: QuerySet) -> tuple[QuerySet, list[OrderingDescriptor]]:
    annotations = {}
    descriptors = []
    index = 0
    new_order_by = []
    for order_by in _get_order_by(qs):
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
    return qs.annotate(**annotations).order_by(*new_order_by), descriptors


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


@strawberry.type(name="Edge", description="An edge in a connection.")
class DjangoCursorEdge(relay.Edge[relay.NodeType]):

    @classmethod
    def resolve_edge(cls, node: NodeType, *, cursor: OrderedCollectionCursor = None) -> Self:
        return cls(cursor=cursor.to_cursor(), node=node)


@strawberry.type(name="Connection", description="A connection to a list of items.")
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

        nodes, ordering_descriptors = annotate_ordering_fields(nodes)

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

        backwards = False
        limit = None
        if first is not None and last is not None:
            #  TODO: implement this edge-case
            raise ValueError("'first' and 'last' together not yet supported")
        elif first is not None:
            if first < 0:
                raise ValueError("Argument 'first' must be a non-negative integer.")
            limit = first
        elif last is not None:
            if last < 0:
                raise ValueError("Argument 'last' must be a non-negative integer.")
            limit = last
            backwards = True

        if backwards:
            raise NotImplementedError('"backwards" not yet supported.')
        if limit is not None:
            nodes = nodes[:limit]

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
            for v in nodes
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
