import strawberry
import pytest
from strawberry_django import ModelResolver, ModelPermissions
from .app.models import User, Group

@pytest.fixture
def context():
    class request:
        class user:
            def has_perms(perms):
                for perm in perms:
                    if perm not in context['permissions']:
                        return False
                return True
    context = {
        'request': request,
        'permissions': [],
    }
    return context

@pytest.fixture
def testdata(db):
    User.objects.bulk_create([
        User(name='a', age=10),
    ])

@pytest.fixture
def schema(testdata):
    class UserResolver(ModelResolver):
        permission_classes = [ModelPermissions]
        fields = ['id', 'name', 'age']
        model = User
    schema = strawberry.Schema(query=UserResolver.query(), mutation=UserResolver.mutation())
    return schema


def test_query_without_context_and_request_objects(schema):
    result = schema.execute_sync('query { users { name age } }')
    assert result.errors[0].message == 'Missing context object'

    result = schema.execute_sync('query { users { name age } }', context_value={})
    assert result.errors[0].message == 'Missing request object'


def test_query_without_permissions(schema, context):
    result = schema.execute_sync(context_value=context,
            query='query { user(id: 1) { name age } }')
    assert result.errors[0].message == 'User does not have app.view_user permission'

    result = schema.execute_sync(context_value=context,
            query='query { users { name age } }')
    assert result.errors[0].message == 'User does not have app.view_user permission'


def test_mutation_without_permissions(schema, context):
    result = schema.execute_sync(context_value=context,
            query='mutation { createUser(data: {name: "hello", age: 1}) { id } }')
    assert result.errors[0].message == 'User does not have app.add_user permission'

    result = schema.execute_sync(context_value=context,
            query='mutation { updateUsers(data: {name: "hello" }) { id } }')
    assert result.errors[0].message == 'User does not have app.change_user permission'

    result = schema.execute_sync(context_value=context,
            query='mutation { deleteUsers { id } }')
    assert result.errors[0].message == 'User does not have app.delete_user permission'


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
