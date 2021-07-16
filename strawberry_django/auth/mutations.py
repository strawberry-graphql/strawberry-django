from django.contrib import auth
from django.contrib.auth.password_validation import validate_password
import strawberry

from strawberry_django.arguments import UNSET
from strawberry_django.mutations.fields import get_input_data
from strawberry_django.mutations.fields import DjangoCreateMutation

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


def login():
    mutation = strawberry.mutation(resolver=resolve_login)
    mutation.is_optional = True
    return mutation


def logout():
    return strawberry.mutation(resolver=resolve_logout)


def register(user_type):
    return DjangoRegisterMutation(user_type)


class DjangoRegisterMutation(DjangoCreateMutation):
    def create(self, data):
        input_data = get_input_data(self.input_type, data)
        validate_password(input_data["password"])

        return super().create(data)
