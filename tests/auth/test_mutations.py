from typing import Optional

import django.contrib.auth as django_auth
import pytest
import strawberry
from django.core.exceptions import ObjectDoesNotExist

import strawberry_django
from strawberry_django import auth, auto
from tests import utils

UserModel = django_auth.get_user_model()


@strawberry_django.type(UserModel)
class User:
    username: auto
    email: auto


@strawberry_django.input(UserModel)
class UserInput:
    username: auto
    password: auto
    email: auto


@pytest.fixture
def user(db, group, tag):
    user = UserModel.objects.create_user(username="user", password="password")
    return user


@strawberry.type
class Mutation:
    login: Optional[User] = auth.login()
    logout = auth.logout()
    register: User = auth.register(UserInput)


@pytest.fixture
def mutation(db):
    return utils.generate_query(mutation=Mutation)


@pytest.fixture
def context(mocker):
    class Session(dict):
        def cycle_key(self):
            pass

        def flush(self):
            pass

    context = mocker.Mock()
    context.request.session = Session()
    django_auth.logout(context.request)
    return context


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
    assert not result.errors
    assert result.data["login"] == None

    assert context.request.user.is_anonymous


def test_logout(mutation, user, context):
    django_auth.login(context.request, user)

    result = mutation("{ logout }", context_value=context)
    assert not result.errors
    assert result.data["logout"] == True

    assert context.request.user.is_anonymous


def test_logout_without_logged_in(mutation, user, context):
    result = mutation("{ logout }", context_value=context)
    assert not result.errors
    assert result.data["logout"] == False


def test_register_new_user(mutation, user, context):
    result = mutation(
        '{ register(data: {username: "new_user", password: "test_password"}) { username } }',
        context_value=context,
    )

    assert not result.errors
    assert result.data["register"] == {"username": "new_user"}

    assert UserModel.objects.get(username="new_user")


def test_register_with_invalid_password(mutation, user, context):
    result = mutation(
        '{ register(data: {username: "invalid_user", password: "a"}) { username } }',
        context_value=context,
    )

    assert len(result.errors) == 1
    assert "too short" in result.errors[0].message

    with pytest.raises(ObjectDoesNotExist):
        assert UserModel.objects.get(username="invalid_user")
