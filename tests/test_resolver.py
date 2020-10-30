import strawberry
import typing
from strawberry_django import ModelResolver
import pytest
from .app.models import DataModel, User

@pytest.fixture(autouse=True)
def data(db):
    return User.objects.create(name='hello', age=1)

class UserResolver(ModelResolver):
    model = User

class DataResolver(ModelResolver):
    model = DataModel

@pytest.fixture
def schema(db):
    @strawberry.type
    class Query:
        items = UserResolver.list_field()
    return strawberry.Schema(query=Query)


def test_basic_resolver(schema):
    result = schema.execute_sync('query { items { name } }')

    assert not result.errors
    assert result.data['items'] == [{
        'name': 'hello',
    }]
