import strawberry
import pytest
from strawberry_django import ModelResolver
from .app.models import User, Group

@pytest.fixture(autouse=True)
def testdata(db):
    User.objects.bulk_create([
        User(name='a', age=10),
        User(name='b', age=20),
        User(name='c', age=20),
    ])
    user_a = User.objects.get(name='a')
    Group.objects.bulk_create([
        Group(name='x', admin=user_a),
        Group(name='y', admin=user_a),
    ])
    user_b = User.objects.get(name='b')
    group = Group.objects.get(name='x')
    group.users.add(user_a, user_b)


@pytest.fixture
def schema(db):
    class UserResolver(ModelResolver):
        model = User
        @strawberry.field
        def age_days(root) -> int:
            return root.age * 365
    class GroupResolver(ModelResolver):
        model = Group
    @strawberry.type
    class Query(UserResolver.query(), GroupResolver.query()):
        pass
    schema = strawberry.Schema(query=Query)
    return schema


def test_query_get(schema):
    result = schema.execute_sync('query { user(id: 1) { name age } }')

    assert not result.errors
    assert result.data['user'] == {'name': 'a', 'age': 10}


def test_query_field(schema):
    result = schema.execute_sync('query { user(id: 1) { age, ageDays } }')

    assert not result.errors
    assert result.data['user'] == {'age': 10, 'ageDays': 3650}


def test_query_list(schema):
    result = schema.execute_sync('query { users { name age } }')

    assert not result.errors
    assert result.data['users'] == [
        {'name': 'a', 'age': 10},
        {'name': 'b', 'age': 20},
        {'name': 'c', 'age': 20},
    ]


def test_query_list_filter(schema):
    result = schema.execute_sync('query { users(filter: "age__gt=10") { name age } }')

    assert not result.errors
    assert result.data['users'] == [
        {'name': 'b', 'age': 20},
        {'name': 'c', 'age': 20},
    ]


def test_query_list_exclude(schema):
    result = schema.execute_sync('query { users(filter: "!age__gt=10") { name age } }')

    assert not result.errors
    assert result.data['users'] == [
        {'name': 'a', 'age': 10},
    ]


def test_query_many_to_many_relation(schema):
    result = schema.execute_sync('query { user(id: 1) { groups { name } } }')

    assert not result.errors
    assert result.data['user']['groups'] == [ {'name': 'x'} ]


def test_query_backward_relation(schema):
    result = schema.execute_sync('query { group(id: 1) { users { name } } }')

    assert not result.errors
    assert result.data['group']['users'] == [
        {'name': 'a'},
        {'name': 'b'},
    ]


def test_query_many_to_one_relation(schema):
    result = schema.execute_sync('query { user(id: 1) { adminGroups { name } } }')

    assert not result.errors
    assert result.data['user']['adminGroups'] == [
        {'name': 'x'},
        {'name': 'y'},
    ]


def test_query_one_to_many_relation(schema):
    result = schema.execute_sync('query { group(id: 1) { admin { name } } }')

    assert not result.errors
    assert result.data['group']['admin'] == {'name': 'a'}
