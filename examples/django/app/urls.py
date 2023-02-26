from strawberry.django.views import AsyncGraphQLView, GraphQLView

from django.urls import path
from django.views.generic.base import RedirectView

from .schema import schema

urlpatterns = [
    path("", RedirectView.as_view(url="graphql")),
    path("graphql/sync", GraphQLView.as_view(schema=schema)),
    path("graphql", AsyncGraphQLView.as_view(schema=schema)),
]
