from __future__ import annotations

from app.base.dataloaders import DataLoaders
from app.base.types import Context
from strawberry.django.views import AsyncGraphQLView


class GraphQLView(AsyncGraphQLView):
    async def get_context(self, request, response):
        return Context(
            request=request,
            response=response,
            dataloaders=DataLoaders(),
        )
