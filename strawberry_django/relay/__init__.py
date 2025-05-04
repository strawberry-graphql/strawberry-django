import warnings
from typing import TYPE_CHECKING, Any

from .cursor_connection import (
    DjangoCursorConnection,
    DjangoCursorEdge,
    OrderedCollectionCursor,
    OrderingDescriptor,
    apply_cursor_pagination,
)
from .list_connection import DjangoListConnection
from .utils import (
    resolve_model_id,
    resolve_model_id_attr,
    resolve_model_node,
    resolve_model_nodes,
)

if TYPE_CHECKING:
    from .list_connection import ListConnectionWithTotalCount  # noqa: F401

__all__ = [
    "DjangoCursorConnection",
    "DjangoCursorEdge",
    "DjangoListConnection",
    "OrderedCollectionCursor",
    "OrderingDescriptor",
    "apply_cursor_pagination",
    "resolve_model_id",
    "resolve_model_id_attr",
    "resolve_model_node",
    "resolve_model_nodes",
]


def __getattr__(name: str) -> Any:
    if name == "ListConnectionWithTotalCount":
        warnings.warn(
            "`ListConnectionWithTotalCount` is deprecated, use `DjangoListConnection` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DjangoListConnection
    raise AttributeError(f"module {__name__} has no attribute {name}")
