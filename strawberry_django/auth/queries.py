from strawberry.types import Info
import strawberry_django
from .utils import get_current_user
from django.contrib.auth.models import AbstractBaseUser


def resolve_current_user(info: Info) -> AbstractBaseUser:
    user = get_current_user()

    if not user.is_authenticated:
        return None

    return user


def current_user():
    return strawberry_django.field(resolver=resolve_current_user)
