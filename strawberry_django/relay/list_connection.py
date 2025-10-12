import inspect
import warnings
from collections.abc import Sized
from typing import TYPE_CHECKING, Any, cast

import strawberry
from django.db import models
from strawberry import Info, relay
from strawberry.relay.types import NodeIterableType
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.types.nodes import InlineFragment, Selection
from strawberry.utils.await_maybe import AwaitableOrValue
from strawberry.utils.inspect import in_async_context
from typing_extensions import Self, deprecated

from strawberry_django.pagination import get_total_count
from strawberry_django.queryset import get_queryset_config
from strawberry_django.resolvers import django_resolver
from strawberry_django.utils.typing import unwrap_type


def _should_optimize_total_count(info: Info) -> bool:
    """Check if the user requested to resolve the `totalCount` field of a connection.

    Taken and adjusted from strawberry.relay.utils
    """
    resolve_for_field_names = {"totalCount"}

    def _check_selection(selection: Selection) -> bool:
        """Recursively inspect the selection to check if the user requested to resolve the `edges` field.

        Args:
            selection (Selection): The selection to check.

        Returns:
            bool: True if the user requested to resolve the `edges` field of a connection, False otherwise.

        """
        if (
            not isinstance(selection, InlineFragment)
            and selection.name in resolve_for_field_names
        ):
            return True
        if selection.selections:
            return any(
                _check_selection(selection) for selection in selection.selections
            )
        return False

    for selection_field in info.selected_fields:
        for selection in selection_field.selections:
            if _check_selection(selection):
                return True
    return False


@strawberry.type(name="Connection", description="A connection to a list of items.")
class DjangoListConnection(relay.ListConnection[relay.NodeType]):
    nodes: strawberry.Private[NodeIterableType[relay.NodeType] | None] = None

    @strawberry.field(description="Total quantity of existing nodes.")
    @django_resolver
    def total_count(self) -> int | None:
        assert self.nodes is not None

        try:
            return self.edges[0].node._strawberry_total_count  # type: ignore
        except (IndexError, AttributeError):
            pass

        if isinstance(self.nodes, models.QuerySet):
            return get_total_count(self.nodes)

        return len(self.nodes) if isinstance(self.nodes, Sized) else None

    @classmethod
    def resolve_connection(
        cls,
        nodes: NodeIterableType[relay.NodeType],
        *,
        info: Info,
        before: str | None = None,
        after: str | None = None,
        first: int | None = None,
        last: int | None = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        if isinstance(nodes, models.QuerySet) and (
            queryset_config := get_queryset_config(nodes)
        ):
            if queryset_config.optimized_by_prefetching:
                try:
                    conn = cls.resolve_optimized_connection_by_prefetch(
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

            if queryset_config.optimized:
                if (last or 0) > 0 and before is None:
                    return cls.resolve_optimized_last_connection(
                        nodes,
                        info=info,
                        before=before,
                        after=after,
                        first=first,
                        last=last,
                        **kwargs,
                    )

                if _should_optimize_total_count(info):
                    nodes = nodes.annotate(
                        _strawberry_total_count=models.Window(
                            expression=models.Count(1), partition_by=None
                        )
                    )

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
    def resolve_optimized_connection_by_prefetch(
        cls,
        nodes: NodeIterableType[relay.NodeType],
        *,
        info: Info,
        before: str | None = None,
        after: str | None = None,
        first: int | None = None,
        last: int | None = None,
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

    @classmethod
    def resolve_optimized_last_connection(
        cls,
        nodes: NodeIterableType[relay.NodeType],
        *,
        info: Info,
        before: str | None = None,
        after: str | None = None,
        first: int | None = None,
        last: int | None = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        """Resolve the connection being paginated only via `last`.

        In order to prevent fetching the entire table, QuerySet is first counted & the
        amount is used instead of `before=None`.
        """
        assert isinstance(nodes, models.QuerySet)

        type_def = get_object_definition(cls)
        assert type_def
        field_def = type_def.get_field("edges")
        assert field_def
        field = field_def.resolve_type(type_definition=type_def)
        field = unwrap_type(field)
        edge_class = cast("relay.Edge[relay.NodeType]", field)

        if in_async_context():

            async def wrapper():
                total_count = await nodes.acount()
                before = relay.to_base64(edge_class.CURSOR_PREFIX, total_count)
                conn = cls.resolve_connection(
                    nodes,
                    info=info,
                    before=before,
                    after=after,
                    first=first,
                    last=last,
                    **kwargs,
                )
                return await conn if inspect.isawaitable(conn) else conn

            return wrapper()

        total_count = nodes.count()
        before = relay.to_base64(edge_class.CURSOR_PREFIX, total_count)
        return cls.resolve_connection(
            nodes,
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
            **kwargs,
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
