from strawberry.types import Info


def get_current_user(info: Info):
    """Get and return the current user based on various scenarios."""
    try:
        user = info.context.request.user
    except AttributeError:
        try:
            # When running queries/mutations in ASGI mode, the user is moved into the consumer scope
            user = info.context.get("request").consumer.scope["user"]
        except AttributeError:
            # When using this through websockets / subscriptions, scope sits inside of the request
            user = info.context.get("request").scope.get("user")

    return user


async def aget_current_user(info: Info):
    return sync_to_async(get_current_user)(info)
