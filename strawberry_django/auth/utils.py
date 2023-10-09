from typing import Optional

from asgiref.sync import sync_to_async
from strawberry.types import Info

from strawberry_django.utils.typing import UserType


def get_current_user(info: Info) -> Optional[UserType]:
    """Get and return the current user based on various scenarios."""
    try:
        user = info.context.request.user
    except AttributeError:
        try:
            # queries/mutations in ASGI move the user into consumer scope
            user = info.context.get("request").consumer.scope["user"]
        except AttributeError:
            # websockets / subscriptions move scope inside of the request
            user = info.context.get("request").scope.get("user")

    # Access an attribute inside the user object to force loading it in async contexts.
    if user is not None:
        _ = user.is_authenticated

    return user


async def aget_current_user(info: Info) -> Optional[UserType]:
    return await sync_to_async(get_current_user)(info)
