import strawberry_django

def resolve_current_user(info):
    if not info.context.request.user.is_authenticated:
        return None
    return info.context.request.user

def current_user():
    field = strawberry_django.field(resolver=resolve_current_user)
    field.is_optional = True
    return field
