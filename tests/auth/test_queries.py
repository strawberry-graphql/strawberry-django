from typing import Optional

import pytest
import strawberry
import strawberry_django
from django.contrib import auth as django_auth
from strawberry_django import auto, auth

from tests import utils
from .test_mutations import User, context, user

@strawberry.type
class Query:
    current_user: Optional[User] = auth.current_user()

@pytest.fixture
def query(db):
    return utils.generate_query(Query)


def test_current_user(query, user, context):
    django_auth.login(context.request, user)

    result = query('{ currentUser { username } }', context_value=context)
    assert not result.errors
    assert result.data == { 'currentUser': { 'username': 'user' } }


def test_current_user_not_logged_in(query, user, context):
    result = query('{ currentUser { username } }', context_value=context)
    assert not result.errors
    assert result.data == { 'currentUser': None }
