from typing import Any

import strawberry
from django.contrib import auth
from django.contrib.auth.password_validation import validate_password

from strawberry_django.mutations.fields import (
    DjangoCreateMutation,
    get_input_data,
    update_m2m,
)

from ..resolvers import django_resolver


@django_resolver
def resolve_login(info, username: str, password: str):
    request = info.context.request
    user = auth.authenticate(request, username=username, password=password)
    if user is not None:
        auth.login(request, user)
        return user
    auth.logout(request)
    return None


@django_resolver
def resolve_logout(info) -> bool:
    request = info.context.request
    ret = request.user.is_authenticated
    auth.logout(request)
    return ret


def login() -> Any:
    mutation = strawberry.mutation(resolver=resolve_login)
    mutation.is_optional = True
    return mutation


def logout() -> bool:
    return strawberry.mutation(resolver=resolve_logout)


def register(user_type) -> Any:
    return DjangoRegisterMutation(user_type)


class DjangoRegisterMutation(DjangoCreateMutation):
    def create(self, data):
        input_data = get_input_data(self.input_type, data)
        validate_password(input_data["password"])
        instance = self.django_model.objects.create_user(**input_data)
        update_m2m([instance], data)
        return instance
