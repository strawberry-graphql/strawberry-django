from django.urls import path
from strawberry.django.views import AsyncGraphQLView, GraphQLView

from .schema import schema


urlpatterns = [
    path("graphql/sync", GraphQLView.as_view(schema=schema)),
    path("graphql", AsyncGraphQLView.as_view(schema=schema)),
]
