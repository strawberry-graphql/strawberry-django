from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.urls import re_path

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack

from strawberry.channels.handlers.http_handler import GraphQLHTTPConsumer
from strawberry.channels.handlers.ws_handler import GraphQLWSConsumer

if TYPE_CHECKING:
    from strawberry.schema import BaseSchema


class AuthGraphQLProtocolTypeRouter(ProtocolTypeRouter):
    """
    Convenience class to set up GraphQL on both HTTP and Websocket whilte enabling AuthMiddlewareStack
    and the AllowedHostsOriginValidator

    ```
    from strawberry_django.routers import AuthGraphQLProtocolTypeRouter
    from django.core.asgi import get_asgi_application

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
        django_application: Optional[str] = None,
        url_pattern: str = "^graphql",
    ):
        http_urls = [re_path(url_pattern, GraphQLHTTPConsumer.as_asgi(schema=schema))]
        if django_application is not None:
            http_urls.append(re_path("^", django_application))

        super().__init__(
            {
                "http": AuthMiddlewareStack(
                    URLRouter(
                        http_urls
                    ),
                ),
                "websocket": AllowedHostsOriginValidator(
                    AuthMiddlewareStack(
                        URLRouter(
                            [
                                re_path(url_pattern, GraphQLWSConsumer.as_asgi(schema=schema)),
                            ],
                        ),
                    ),
                ),
            }
        )
