import strawberry_django


def get_current_user(info):
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


def resolve_current_user(info):
    user = get_current_user()

    if not user.is_authenticated:
        return None

    return user


def current_user():
    return strawberry_django.field(resolver=resolve_current_user)
