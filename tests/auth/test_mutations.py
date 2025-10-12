import django.contrib.auth as django_auth
import pytest
import strawberry
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import strawberry_django
from strawberry_django import auth
from tests import utils

UserModel = django_auth.get_user_model()


@strawberry_django.type(UserModel)
class User:
    username: strawberry.auto
    email: strawberry.auto


@strawberry_django.input(UserModel)
class UserInput:
    username: strawberry.auto
    password: strawberry.auto
    email: strawberry.auto


@strawberry.type
class Mutation:
    login: User | None = auth.login()  # type: ignore
    logout = auth.logout()
    register: User = auth.register(UserInput)


@pytest.fixture
def mutation(db):
    return utils.generate_query(mutation=Mutation)


def test_login(mutation, user, context):
    result = mutation(
        '{ login(username: "user", password: "password") { username } }',
        context_value=context,
    )
    assert not result.errors
    assert result.data["login"] == {"username": "user"}

    assert context.request.user == user


def test_login_with_wrong_password(mutation, user, context):
    result = mutation(
        '{ login(username: "user", password: "wrong") { username } }',
        context_value=context,
    )
    assert result.errors
    assert result.data["login"] is None

    assert context.request.user.is_anonymous


def test_logout(mutation, user, context):
    django_auth.login(
        context.request,
        user,
        backend=settings.AUTHENTICATION_BACKENDS[0],
    )

    result = mutation("{ logout }", context_value=context)
    assert not result.errors
    assert result.data["logout"] is True

    assert context.request.user.is_anonymous


def test_logout_without_logged_in(mutation, user, context):
    result = mutation("{ logout }", context_value=context)
    assert not result.errors
    assert result.data["logout"] is False


def test_register_new_user(mutation, user, context):
    result = mutation(
        '{ register(data: {username: "new_user",'
        ' password: "test_password"}) { username } }',
        context_value=context,
    )

    assert not result.errors
    assert result.data["register"] == {"username": "new_user"}

    user = UserModel.objects.get(username="new_user")
    assert user.pk
    assert user.check_password("test_password")


def test_register_with_invalid_password(mutation, user, context):
    result = mutation(
        '{ register(data: {username: "invalid_user", password: "a"}) { username } }',
        context_value=context,
    )

    assert len(result.errors) == 1
    assert "too short" in result.errors[0].message

    with pytest.raises(ObjectDoesNotExist):
        assert UserModel.objects.get(username="invalid_user")
