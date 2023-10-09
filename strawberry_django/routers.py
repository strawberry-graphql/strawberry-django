from __future__ import annotations

from typing import TYPE_CHECKING

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import URLPattern, URLResolver, re_path
from strawberry.channels.handlers.http_handler import GraphQLHTTPConsumer
from strawberry.channels.handlers.ws_handler import GraphQLWSConsumer

if TYPE_CHECKING:
    from django.core.handlers.asgi import ASGIHandler
    from strawberry.schema import BaseSchema


class AuthGraphQLProtocolTypeRouter(ProtocolTypeRouter):
    """Convenience class to set up GraphQL on both HTTP and Websocket.

     This convenience class will include AuthMiddlewareStack and the
     AllowedHostsOriginValidator to ensure you have user object available.

    ```
    from strawberry_django.routers import AuthGraphQLProtocolTypeRouter
    from django.core.asgi import get_asgi_application.

    django_asgi = get_asgi_application()

    from myapi import schema

    application = AuthGraphQLProtocolTypeRouter(
        schema,
        django_application=django_asgi,
    )
    ```

    This will route all requests to /graphql on either HTTP or websockets to us,
    and everything else to the Django application.
    """

    def __init__(
        self,
        schema: BaseSchema,
        django_application: ASGIHandler | None = None,
        url_pattern: str = "^graphql",
    ):
        http_urls: list[URLPattern | URLResolver] = [
            re_path(url_pattern, GraphQLHTTPConsumer.as_asgi(schema=schema)),
        ]
        if django_application is not None:
            http_urls.append(re_path(r"^", django_application))

        super().__init__(
            {
                "http": AuthMiddlewareStack(
                    URLRouter(
                        http_urls,
                    ),
                ),
                "websocket": AllowedHostsOriginValidator(
                    AuthMiddlewareStack(
                        URLRouter(
                            [
                                re_path(
                                    url_pattern,
                                    GraphQLWSConsumer.as_asgi(schema=schema),
                                ),
                            ],
                        ),
                    ),
                ),
            },
        )
