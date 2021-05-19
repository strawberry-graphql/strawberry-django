import strawberry_django

def resolve_current_user(info):
    return info.context.request.user

def current_user():
    return strawberry_django.field(resolver=resolve_current_user)
