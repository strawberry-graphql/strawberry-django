from strawberry.types import Info

import strawberry_django

from .utils import get_current_user


def resolve_current_user(info: Info):
    user = get_current_user(info)

    if not user.is_authenticated:
        return None

    return user


def current_user():
    return strawberry_django.field(resolver=resolve_current_user)
