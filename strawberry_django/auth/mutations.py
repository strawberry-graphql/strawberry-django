import functools
from typing import TYPE_CHECKING

import strawberry
from django.contrib import auth
from django.contrib.auth.password_validation import validate_password
from strawberry.types import Info

from strawberry_django.mutations import mutations
from strawberry_django.mutations.fields import (
    DjangoCreateMutation,
    get_input_data,
    update_m2m,
)
from strawberry_django.resolvers import django_resolver


@django_resolver
def resolve_login(info: Info, username: str, password: str):
    request = info.context.request
    user = auth.authenticate(request, username=username, password=password)
    if user is not None:
        auth.login(request, user)
        return user
    auth.logout(request)
    return None


@django_resolver
def resolve_logout(info: Info) -> bool:
    request = info.context.request
    ret = request.user.is_authenticated
    auth.logout(request)
    return ret


class DjangoRegisterMutation(DjangoCreateMutation):
    def create(self, data: type):
        assert self.input_type is not None
        input_data = get_input_data(self.input_type, data)
        validate_password(input_data["password"])
        assert self.django_model
        instance = self.django_model._default_manager.create_user(  # type: ignore
            **input_data,
        )
        update_m2m([instance], data)
        return instance


login = functools.partial(strawberry.mutation, resolver=resolve_login)
logout = functools.partial(strawberry.mutation, resolver=resolve_logout)
register = mutations.create if TYPE_CHECKING else DjangoRegisterMutation
