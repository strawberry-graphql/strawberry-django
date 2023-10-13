from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Type, cast

import strawberry
from django.contrib import auth
from django.contrib.auth.password_validation import validate_password

from strawberry_django.mutations import mutations, resolvers
from strawberry_django.mutations.fields import DjangoCreateMutation
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.resolvers import django_resolver
from strawberry_django.utils.requests import get_request

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from strawberry.types import Info


@django_resolver
def resolve_login(info: Info, username: str, password: str) -> AbstractBaseUser | None:
    request = get_request(info)
    user = auth.authenticate(request, username=username, password=password)

    if user is not None:
        auth.login(request, user)
        return user

    auth.logout(request)
    return None


@django_resolver
def resolve_logout(info: Info) -> bool:
    request = get_request(info)
    ret = request.user.is_authenticated
    auth.logout(request)
    return ret


class DjangoRegisterMutation(DjangoCreateMutation):
    def create(self, data: dict[str, Any], *, info: Info):
        model = cast(Type["AbstractBaseUser"], self.django_model)
        assert model is not None

        password = data.pop("password")
        validate_password(password)

        # Do not optimize anything while retrieving the object to update
        with DjangoOptimizerExtension.disabled():
            return resolvers.create(
                info,
                model,
                data,
                full_clean=self.full_clean,
                pre_save_hook=lambda obj: obj.set_password(password),
            )


login = functools.partial(strawberry.mutation, resolver=resolve_login)
logout = functools.partial(strawberry.mutation, resolver=resolve_logout)
register = mutations.create if TYPE_CHECKING else DjangoRegisterMutation
