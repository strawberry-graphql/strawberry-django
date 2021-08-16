from typing import Optional

import pytest
import strawberry
import strawberry_django
from django.contrib import auth as django_auth
from strawberry_django import auto, auth

from tests import utils


@strawberry_django.type(django_auth.models.User)
class User:
    username: auto
    email: auto

@pytest.fixture
def user(db, group, tag):
    user = django_auth.models.User.objects.create_user(username='user', password='password')
    return user

@strawberry.type
class Mutation:
    login: Optional[User] = auth.login()
    logout = auth.logout()

@pytest.fixture
def mutation(db):
    return utils.generate_query(mutation=Mutation)

@pytest.fixture
def context(mocker):
    class Session(dict):
        def cycle_key(self): pass
        def flush(self): pass
    context = mocker.Mock()
    context.request.session = Session()
    django_auth.logout(context.request)
    return context


def test_login(mutation, user, context):
    result = mutation('{ login(username: "user", password: "password") { username } }', context_value=context)
    assert not result.errors
    assert result.data['login'] == { 'username': 'user' }

    assert context.request.user == user


def test_login_with_wrong_password(mutation, user, context):
    result = mutation('{ login(username: "user", password: "wrong") { username } }', context_value=context)
    assert not result.errors
    assert result.data['login'] == None

    assert context.request.user.is_anonymous


def test_logout(mutation, user, context):
    django_auth.login(context.request, user)

    result = mutation('{ logout }', context_value=context)
    assert not result.errors
    assert result.data['logout'] == True

    assert context.request.user.is_anonymous


def test_logout_without_logged_int(mutation, user, context):
    result = mutation('{ logout }', context_value=context)
    assert not result.errors
    assert result.data['logout'] == False
