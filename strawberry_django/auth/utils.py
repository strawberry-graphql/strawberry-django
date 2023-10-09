from asgiref.sync import sync_to_async
from strawberry.types import Info


def get_current_user(info: Info):
    """Get and return the current user based on various scenarios."""
    try:
        user = info.context.request.user
    except AttributeError:
        try:
            # queries/mutations in ASGI move the user into consumer scope
            user = info.context.get("request").consumer.scope["user"]
        except AttributeError:
            # websockets / subscriptions move scope inside of the request
            try:
                user = info.context.get("request").scope.get("user")
            except AttributeError:
                # When running tests, we must manually add a context.
                # For now let's grab it here:
                is_test_mode = info.context.get("is_test_mode")
                if is_test_mode:
                    user = info.context.get("user")
                else:
                    raise

    # Access an attribute inside the user object to force loading it in async contexts.
    if user is not None:
        _ = user.is_authenticated

    return user


async def aget_current_user(info: Info):
    return sync_to_async(get_current_user)(info)
