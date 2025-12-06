from __future__ import annotations

from typing import TYPE_CHECKING

from app.base.dataloaders import DataLoaders
from app.base.types import Context
from strawberry.django.views import AsyncGraphQLView

if TYPE_CHECKING:
    from strawberry.types import ExecutionContext


class GraphQLView(AsyncGraphQLView[Context]):
    """Custom async GraphQL view with typed context.

    Extends AsyncGraphQLView to provide a custom Context class with:
    - Type-safe user access helpers
    - DataLoader instances for query optimization

    The AsyncGraphQLView is required when using async resolvers.
    For sync-only applications, use the standard GraphQLView instead.
    """

    async def get_context(self, request, response) -> Context | ExecutionContext:
        """Create a new Context instance for each GraphQL request.

        IMPORTANT: DataLoaders must be instantiated per-request to ensure
        proper batching and caching within a single request context.

        Args:
            request: The Django HTTP request
            response: The Django HTTP response

        Returns:
            Context instance with request, response, and fresh dataloaders

        """
        return Context(
            request=request,
            response=response,
            dataloaders=DataLoaders(),
        )
