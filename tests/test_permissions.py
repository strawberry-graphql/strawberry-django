import strawberry
import pytest
from strawberry_django import ModelResolver
from .app.models import User, Group

@pytest.fixture
def context():
    context = { 'permissions': [] }
    class request:
        class user:
            def has_perms(perms):
                for perm in perms:
                    if perm not in context['permissions']:
                        return False
                return True
    context['request'] = request
    return context

@pytest.fixture
def testdata(db):
    User.objects.bulk_create([
        User(name='a', age=10),
    ])

@pytest.fixture
def schema(testdata):
    class UserResolver(ModelResolver):
        model = User
    schema = strawberry.Schema(query=UserResolver.query(), mutation=UserResolver.mutation())
    return schema


def test_get_without_request_object(schema):
    result = schema.execute_sync('query { users { name age } }')

    assert not result.errors
    assert result.data['users'] == [ {'name': 'a', 'age': 10} ]


def test_query_without_permissions(schema, context):
    result = schema.execute_sync(context_value=context,
            query='query { user(id: 1) { name age } }')
    assert 'Permission denied' in str(result.errors)

    result = schema.execute_sync(context_value=context,
            query='query { users { name age } }')
    assert 'Permission denied' in str(result.errors)


def test_mutation_without_permissions(schema, context):
    result = schema.execute_sync(context_value=context,
            query='mutation { createUser(data: {name: "hello", age: 1}) { id } }')
    assert 'Permission denied' in str(result.errors)

    result = schema.execute_sync(context_value=context,
            query='mutation { updateUsers(data: {name: "hello" }) { id } }')
    assert 'Permission denied' in str(result.errors)

    result = schema.execute_sync(context_value=context,
            query='mutation { deleteUsers { id } }')
    assert 'Permission denied' in str(result.errors)


def test_view_permissions(schema, context):
    context['permissions'] = ['app.view_user']

    result = schema.execute_sync(context_value=context,
            query='query { user(id: 1) { name age } }')
    assert not result.errors

    result = schema.execute_sync(context_value=context,
            query='query { users { name age } }')
    assert not result.errors


def test_add_permissions(schema, context):
    context['permissions'] = ['app.add_user']

    result = schema.execute_sync(context_value=context,
            query='mutation { createUser(data: {name: "hello", age: 1}) { id } }')
    assert not result.errors


def test_change_permissions(schema, context):
    context['permissions'] = ['app.change_user']

    result = schema.execute_sync(context_value=context,
            query='mutation { updateUsers(data: {name: "hello" }) { id } }')
    assert not result.errors


def test_delete_permissions(schema, context):
    context['permissions'] = ['app.delete_user']

    result = schema.execute_sync(context_value=context,
            query='mutation { deleteUsers { id } }')
    assert not result.errors
