import pytest
import strawberry
from strawberry_django import ModelResolver
from .app.models import User, Group

@pytest.fixture(autouse=True)
def testdata(db):
    User.objects.bulk_create([
        User(name='a', age=10),
        User(name='b', age=20),
        User(name='c', age=20),
    ])
    Group.objects.create(name='x', admin_id=3)


@pytest.fixture
def schema(testdata):
    class UserResolver(ModelResolver):
        model = User
    class GroupResolver(ModelResolver):
        model = Group
    @strawberry.type
    class Mutation(UserResolver.mutation(), GroupResolver.mutation()):
        pass
    schema = strawberry.Schema(query=UserResolver.query(), mutation=Mutation)
    return schema


def test_mutation_create(schema):
    result = schema.execute_sync('mutation { user: createUsers(data: {name: "x", age: 1}) { id name age } }')

    assert not result.errors
    assert result.data['user'][0]['name'] == 'x'
    assert result.data['user'][0]['age'] == 1

    user = User.objects.get(id=result.data['user'][0]['id'])
    assert user.name == 'x'
    assert user.age == 1


def test_batch_mutation_create(schema):
    result = schema.execute_sync('''
    mutation {
        user: createUsers(data: [
            {name: "d", age: 1},
            {name: "e", age: 2}
        ]) {
            id
            name
            age
        }
    }''')

    assert not result.errors
    assert result.data['user'][0]['name'] == 'd'
    assert result.data['user'][0]['age'] == 1
    assert result.data['user'][1]['name'] == 'e'
    assert result.data['user'][1]['age'] == 2

    user = User.objects.get(id=result.data['user'][0]['id'])
    assert user.name == 'd'
    assert user.age == 1
    user = User.objects.get(id=result.data['user'][1]['id'])
    assert user.name == 'e'
    assert user.age == 2


def test_mutation_update(schema):
    result = schema.execute_sync('mutation { users: updateUsers(data: {name: "y"}, filters: ["id=2"]) { name } }')

    assert not result.errors
    assert result.data['users'][0]['name'] == 'y'

    user = User.objects.get(id=2)
    assert user.name == 'y'


def test_mutation_delete(schema):
    assert User.objects.count() == 3

    result = schema.execute_sync('mutation { users: deleteUsers(filters: ["id=2"]) { id } }')

    assert not result.errors
    assert result.data['users'][0]['id'] == '2'

    assert User.objects.filter(id=2).count() == 0
    assert User.objects.count() == 2


def test_mutation_create_with_relation(schema):
    result = schema.execute_sync('mutation { group: createGroups(data: {name: "x", admin: 3}) { admin { name }} }')

    assert not result.errors
    assert result.data['group'][0]['admin']['name'] == 'c'


def test_mutation_update_relation(schema):
    result = schema.execute_sync('mutation { group: updateGroups(data: {admin: 2}) { admin { name }} }')

    assert not result.errors
    assert result.data['group'][0]['admin']['name'] == 'b'
