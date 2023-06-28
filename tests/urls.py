from django.conf.urls.static import static
from django.urls import path
from django.urls.conf import include
from strawberry.django.views import AsyncGraphQLView, GraphQLView

from .projects.schema import schema

urlpatterns = [
    path("graphql/", GraphQLView.as_view(schema=schema)),
    path("graphql_async/", AsyncGraphQLView.as_view(schema=schema)),
    path("__debug__/", include("debug_toolbar.urls")),
    *static("/media"),
]
