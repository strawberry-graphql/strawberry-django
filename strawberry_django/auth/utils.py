from typing import Literal, Optional, overload

from asgiref.sync import sync_to_async
from strawberry.types import Info

from strawberry_django.utils.typing import UserType


@overload
def get_current_user(info: Info, *, strict: Literal[True]) -> UserType: ...


@overload
def get_current_user(info: Info, *, strict: bool = False) -> Optional[UserType]: ...


def get_current_user(info: Info, *, strict: bool = False) -> Optional[UserType]:
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

    if user is None:
        raise ValueError("No user found in the current request")

    # Access an attribute inside the user object to force loading it in async contexts.
    if user is not None:
        _ = user.is_authenticated

    return user


@overload
async def aget_current_user(
    info: Info,
    *,
    strict: Literal[True],
) -> UserType: ...


@overload
async def aget_current_user(
    info: Info,
    *,
    strict: bool = False,
) -> Optional[UserType]: ...


async def aget_current_user(info: Info, *, strict: bool = False) -> Optional[UserType]:
    return await sync_to_async(get_current_user)(info, strict=strict)
