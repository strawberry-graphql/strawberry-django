import base64
import dataclasses
import functools
import inspect
import json
import warnings
from collections.abc import Iterable, Sized, Collection
from json import JSONDecodeError
from typing import (
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

import strawberry
from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import QuerySet
from strawberry import relay
from strawberry.relay import NodeType, to_base64, from_base64
from strawberry.relay.exceptions import NodeIDAnnotationError
from strawberry.relay.types import NodeIterableType
from strawberry.relay.utils import SliceMetadata
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.types.info import Info
from strawberry.utils.await_maybe import AwaitableOrValue
from typing_extensions import Literal, Self, ClassVar

from strawberry_django.pagination import get_total_count
from strawberry_django.queryset import run_type_get_queryset
from strawberry_django.resolvers import django_getattr, django_resolver
from strawberry_django.utils.inspect import get_model_fields
from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    get_django_definition,
)

_T = TypeVar("_T")
_M = TypeVar("_M", bound=models.Model)


__all__ = [
    "ListConnectionWithTotalCount",
    "resolve_model_id",
    "resolve_model_id_attr",
    "resolve_model_node",
    "resolve_model_nodes",
]


@dataclasses.dataclass
class OrderedCollectionCursor:
    PREFIX: ClassVar[str] = 'orderedcursor'

    field_values: list[str]

    @classmethod
    def from_model(cls, model: models.Model, field_names: list[str]) -> Self:
        model_fields = get_model_fields(type(model))
        values = []
        for field_name in field_names:
            model_field = model_fields[field_name]
            assert isinstance(model_field, models.Field)
            values.append(model_field.value_to_string(model))  # type: ignore
        return values

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

    def apply(self, qs: QuerySet, mode: Literal['before', 'after']) -> QuerySet:
        return qs


@strawberry.type(name="Connection", description="A connection to a list of items.")
class DjangoCursorConnection(relay.Connection[relay.NodeType]):

    cursor_fields: Collection[str] = ('pk', )

    @classmethod
    def resolve_connection(cls, nodes: NodeIterableType[NodeType], *, info: Info, before: Optional[str] = None,
                           after: Optional[str] = None, first: Optional[int] = None, last: Optional[int] = None,
                           max_results: Optional[int] = None, **kwargs: Any) -> AwaitableOrValue[Self]:
        if not isinstance(nodes, QuerySet):
            raise TypeError('DjangoCursorConnection requires a QuerySet')
        if after:
            after_cursor = OrderedCollectionCursor.from_cursor(after)
            nodes = after_cursor.apply(nodes, 'after')
        if before:
            before_cursor = OrderedCollectionCursor.from_cursor(before)
            nodes = before_cursor.apply(nodes, 'before')

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





@strawberry.type(name="Connection", description="A connection to a list of items.")
class ListConnectionWithTotalCount(relay.ListConnection[relay.NodeType]):
    nodes: strawberry.Private[Optional[NodeIterableType[relay.NodeType]]] = None

    @strawberry.field(description="Total quantity of existing nodes.")
    @django_resolver
    def total_count(self) -> Optional[int]:
        assert self.nodes is not None

        if isinstance(self.nodes, models.QuerySet):
            return get_total_count(self.nodes)

        return len(self.nodes) if isinstance(self.nodes, Sized) else None

    @classmethod
    def resolve_connection(
        cls,
        nodes: NodeIterableType[relay.NodeType],
        *,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        from strawberry_django.optimizer import is_optimized_by_prefetching

        if isinstance(nodes, models.QuerySet) and is_optimized_by_prefetching(nodes):
            try:
                conn = cls.resolve_connection_from_cache(
                    nodes,
                    info=info,
                    before=before,
                    after=after,
                    first=first,
                    last=last,
                    **kwargs,
                )
            except AttributeError:
                warnings.warn(
                    (
                        "Pagination annotations not found, falling back to QuerySet resolution. "
                        "This might cause N+1 issues..."
                    ),
                    RuntimeWarning,
                    stacklevel=2,
                )
            else:
                conn = cast("Self", conn)
                conn.nodes = nodes
                return conn

        conn = super().resolve_connection(
            nodes,
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
            **kwargs,
        )

        if inspect.isawaitable(conn):

            async def wrapper():
                resolved = await conn
                resolved.nodes = nodes
                return resolved

            return wrapper()

        conn = cast("Self", conn)
        conn.nodes = nodes
        return conn

    @classmethod
    def resolve_connection_from_cache(
        cls,
        nodes: NodeIterableType[relay.NodeType],
        *,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        """Resolve the connection from the prefetched cache.

        NOTE: This will try to access `node._strawberry_total_count` and
        `node._strawberry_row_number` attributes from the nodes. If they
        don't exist, `AttriuteError` will be raised, meaning that we should
        fallback to the queryset resolution.
        """
        result = nodes._result_cache  # type: ignore

        type_def = get_object_definition(cls, strict=True)
        field_def = type_def.get_field("edges")
        assert field_def

        field = field_def.resolve_type(type_definition=type_def)
        while isinstance(field, StrawberryContainer):
            field = field.of_type

        edge_class = cast("relay.Edge[relay.NodeType]", field)

        edges: list[relay.Edge] = [
            edge_class.resolve_edge(
                cls.resolve_node(node, info=info, **kwargs),
                cursor=node._strawberry_row_number - 1,
            )
            for node in result
        ]
        has_previous_page = result[0]._strawberry_row_number > 1 if result else False
        has_next_page = (
            result[-1]._strawberry_row_number < result[-1]._strawberry_total_count
            if result
            else False
        )

        return cls(
            edges=edges,
            page_info=relay.PageInfo(
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
                has_previous_page=has_previous_page,
                has_next_page=has_next_page,
            ),
        )


def get_node_caster(origin: Optional[type]) -> Callable[[_T], _T]:
    if origin is None:
        return lambda node: node

    return functools.partial(strawberry.cast, origin)


@overload
def resolve_model_nodes(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    *,
    info: Optional[Info] = None,
    node_ids: Iterable[Union[str, relay.GlobalID]],
    required: Literal[True],
    filter_perms: bool = False,
) -> AwaitableOrValue[Iterable[_M]]: ...


@overload
def resolve_model_nodes(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    *,
    info: Optional[Info] = None,
    node_ids: None = None,
    required: Literal[True],
    filter_perms: bool = False,
) -> AwaitableOrValue[models.QuerySet[_M]]: ...


@overload
def resolve_model_nodes(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    *,
    info: Optional[Info] = None,
    node_ids: Iterable[Union[str, relay.GlobalID]],
    required: Literal[False],
    filter_perms: bool = False,
) -> AwaitableOrValue[Iterable[Optional[_M]]]: ...


@overload
def resolve_model_nodes(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    *,
    info: Optional[Info] = None,
    node_ids: None = None,
    required: Literal[False],
    filter_perms: bool = False,
) -> AwaitableOrValue[Optional[models.QuerySet[_M]]]: ...


@overload
def resolve_model_nodes(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    *,
    info: Optional[Info] = None,
    node_ids: Optional[Iterable[Union[str, relay.GlobalID]]] = None,
    required: bool = False,
    filter_perms: bool = False,
) -> AwaitableOrValue[
    Union[
        Iterable[_M],
        models.QuerySet[_M],
        Iterable[Optional[_M]],
        Optional[models.QuerySet[_M]],
    ]
]: ...


def resolve_model_nodes(
    source,
    *,
    info=None,
    node_ids=None,
    required=False,
    filter_perms=False,
) -> AwaitableOrValue[
    Union[
        Iterable[_M],
        models.QuerySet[_M],
        Iterable[Optional[_M]],
        Optional[models.QuerySet[_M]],
    ]
]:
    """Resolve model nodes, ensuring those are prefetched in a sync context.

    Args:
    ----
        source:
            The source model or the model type that implements the `Node` interface
        info:
            Optional gql execution info. Make sure to always provide this or
            otherwise, the queryset cannot be optimized in case DjangoOptimizerExtension
            is enabled. This will also be used for `is_awaitable` check.
        node_ids:
            Optional filter by those node_ids instead of retrieving everything
        required:
            If `True`, all `node_ids` requested must exist. If they don't,
            an error must be raised. If `False`, missing nodes should be
            returned as `None`. It only makes sense when passing a list of
            `node_ids`, otherwise it will should ignored.

    Returns:
    -------
        The resolved queryset, already prefetched from the database

    """
    from strawberry_django import optimizer  # avoid circular import
    from strawberry_django.permissions import filter_with_perms

    if issubclass(source, models.Model):
        origin = None
    else:
        origin = source
        django_type = get_django_definition(source, strict=True)
        source = cast("type[_M]", django_type.model)

    qs = cast("models.QuerySet[_M]", source._default_manager.all())
    qs = run_type_get_queryset(qs, origin, info)

    id_attr = cast("relay.Node", origin).resolve_id_attr()
    if node_ids is not None:
        qs = qs.filter(
            **{
                f"{id_attr}__in": [
                    i.node_id if isinstance(i, relay.GlobalID) else i for i in node_ids
                ],
            },
        )

    extra_args = {}
    if info is not None:
        if filter_perms:
            qs = filter_with_perms(qs, info)

        # Connection will filter the results when its is being resolved.
        # We don't want to fetch everything before it does that
        return_type = info.return_type
        if isinstance(return_type, type) and issubclass(return_type, relay.Connection):
            extra_args["qs_hook"] = lambda qs: qs

        ext = optimizer.optimizer.get()
        if ext is not None:
            # If optimizer extension is enabled, optimize this queryset
            qs = ext.optimize(qs, info=info)

    retval = cast(
        "AwaitableOrValue[models.QuerySet[_M]]",
        django_resolver(lambda _qs: _qs, **extra_args)(qs),
    )
    if not node_ids:
        return retval

    def map_results(results: models.QuerySet[_M]) -> list[_M]:
        node_caster = get_node_caster(origin)
        results_map = {str(getattr(obj, id_attr)): node_caster(obj) for obj in results}
        retval: list[Optional[_M]] = []
        for node_id in node_ids:
            if required:
                retval.append(results_map[str(node_id)])
            else:
                retval.append(results_map.get(str(node_id), None))

        return retval  # type: ignore

    if inspect.isawaitable(retval):

        async def async_resolver():
            return await sync_to_async(map_results)(await retval)

        return async_resolver()

    return map_results(retval)


@overload
def resolve_model_node(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    node_id: Union[str, relay.GlobalID],
    *,
    info: Optional[Info] = ...,
    required: Literal[False] = ...,
    filter_perms: bool = False,
) -> AwaitableOrValue[Optional[_M]]: ...


@overload
def resolve_model_node(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    node_id: Union[str, relay.GlobalID],
    *,
    info: Optional[Info] = ...,
    required: Literal[True],
    filter_perms: bool = False,
) -> AwaitableOrValue[_M]: ...


def resolve_model_node(
    source,
    node_id,
    *,
    info: Optional[Info] = None,
    required=False,
    filter_perms=False,
):
    """Resolve model nodes, ensuring it is retrieved in a sync context.

    Args:
    ----
        source:
            The source model or the model type that implements the `Node` interface
        node_id:
            The node it to retrieve the model from
        info:
            Optional gql execution info. Make sure to always provide this or
            otherwise, the queryset cannot be optimized in case DjangoOptimizerExtension
            is enabled. This will also be used for `is_awaitable` check.
        required:
            If the return value is required to exist. If true, `qs.get()` will be
            used, which might raise `model.DoesNotExist` error if the node doesn't
            exist. Otherwise, `qs.first()` will be used, which might return None.

    Returns:
    -------
        The resolved node, already prefetched from the database

    """
    from strawberry_django import optimizer  # avoid circular import
    from strawberry_django.permissions import filter_with_perms

    if issubclass(source, models.Model):
        origin = None
    else:
        origin = source
        django_type = get_django_definition(source, strict=True)
        source = cast("type[models.Model]", django_type.model)

    if isinstance(node_id, relay.GlobalID):
        node_id = node_id.node_id

    id_attr = cast("relay.Node", origin).resolve_id_attr()
    qs = source._default_manager.all()
    qs = run_type_get_queryset(qs, origin, info)

    qs = qs.filter(**{id_attr: node_id})

    if info is not None:
        if filter_perms:
            qs = filter_with_perms(qs, info)

        ext = optimizer.optimizer.get()
        if ext is not None:
            # If optimizer extension is enabled, optimize this queryset
            qs = ext.optimize(qs, info=info)

    node_caster = get_node_caster(origin)
    return django_resolver(lambda: node_caster(qs.get() if required else qs.first()))()


def resolve_model_id_attr(source: type) -> str:
    """Resolve the model id, ensuring it is retrieved in a sync context.

    Args:
    ----
        source:
            The source model type that implements the `Node` interface

    Returns:
    -------
        The resolved id attr

    """
    try:
        id_attr = super(source, source).resolve_id_attr()  # type: ignore
    except NodeIDAnnotationError:
        id_attr = "pk"

    return id_attr


def resolve_model_id(
    source: Union[
        type[WithStrawberryDjangoObjectDefinition],
        type[relay.Node],
        type[_M],
    ],
    root: models.Model,
    *,
    info: Optional[Info] = None,
) -> AwaitableOrValue[str]:
    """Resolve the model id, ensuring it is retrieved in a sync context.

    Args:
    ----
        source:
            The source model or the model type that implements the `Node` interface
        root:
            The source model object.

    Returns:
    -------
        The resolved object id

    """
    id_attr = cast("relay.Node", source).resolve_id_attr()

    assert isinstance(root, models.Model)
    if id_attr == "pk":
        pk = root.__class__._meta.pk
        assert pk
        id_attr = pk.attname

    assert id_attr
    try:
        # Prefer to retrieve this from the cache
        return str(root.__dict__[id_attr])
    except KeyError:
        return django_getattr(root, id_attr)
