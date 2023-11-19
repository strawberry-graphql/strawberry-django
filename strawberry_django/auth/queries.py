from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry_django

from .exceptions import UserNotLoggedInError
from .utils import get_current_user

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from strawberry.types import Info


def resolve_current_user(info: Info) -> AbstractBaseUser:
    user = get_current_user(info)

    if not getattr(user, "is_authenticated", False):
        raise UserNotLoggedInError()  # noqa: RSE102

    return user


def current_user():
    return strawberry_django.field(resolver=resolve_current_user)
