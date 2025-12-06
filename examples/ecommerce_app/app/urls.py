"""URL configuration for example project."""

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import settings
from .schema import schema
from .views import GraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "graphql/",
        GraphQLView.as_view(
            graphiql=settings.DEBUG,
            schema=schema,
        ),
    ),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
