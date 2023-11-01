from django.http.request import HttpRequest
from strawberry.types import Info


def get_request(info: Info) -> HttpRequest:
    """Return the request from Info.

    description:
    Return the request object for both WSGI and ASGI implementations.
    It tends to move based on the environment.
    """
    try:
        request = info.context.request
    except AttributeError:
        request = info.context.get("request")

    return request
