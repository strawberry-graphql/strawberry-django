from __future__ import annotations

from typing import TYPE_CHECKING

from app.base.dataloaders import DataLoaders
from app.base.types import Context
from strawberry.django.views import AsyncGraphQLView

if TYPE_CHECKING:
    from strawberry.types import ExecutionContext


class GraphQLView(AsyncGraphQLView[Context]):
    async def get_context(self, request, response) -> Context | ExecutionContext:  # pyright: ignore[reportIncompatibleMethodOverride]
        return Context(
            request=request,
            response=response,
            dataloaders=DataLoaders(),
        )
