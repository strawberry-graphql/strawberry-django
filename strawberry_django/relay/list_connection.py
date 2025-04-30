import inspect
import warnings
from collections.abc import Sized
from typing import TYPE_CHECKING, Any, Optional, cast

import strawberry
from django.db import models
from strawberry import Info, relay
from strawberry.relay.types import NodeIterableType
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.utils.await_maybe import AwaitableOrValue
from typing_extensions import Self, deprecated

from strawberry_django.pagination import get_total_count
from strawberry_django.resolvers import django_resolver


@strawberry.type(name="Connection", description="A connection to a list of items.")
class DjangoListConnection(relay.ListConnection[relay.NodeType]):
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


if TYPE_CHECKING:

    @deprecated(
        "`ListConnectionWithTotalCount` is deprecated, use `DjangoListConnection` instead."
    )
    class ListConnectionWithTotalCount(DjangoListConnection): ...


def __getattr__(name: str) -> Any:
    if name == "ListConnectionWithTotalCount":
        warnings.warn(
            "`ListConnectionWithTotalCount` is deprecated, use `DjangoListConnection` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DjangoListConnection
    raise AttributeError(f"module {__name__} has no attribute {name}")
