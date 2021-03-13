import pytest
import strawberry
import strawberry_django
from .. import models

@pytest.fixture
def users(db):
    users = [ models.User.objects.create(name=f'user{i+1}') for i in range(3) ]

def test_create(mutation):
    result = mutation('{ user: createUser(data: { name: "user1" }) { id name } }')
    assert not result.errors
    assert result.data['user'] == { 'id': '1', 'name': 'user1' }
    assert list(models.User.objects.values('id', 'name')) == [
        { 'id': 1, 'name': 'user1' },
    ]

def test_create_batch(mutation):
    result = mutation('{ users: createUsers(data: [{ name: "user1" }, { name: "user2" }]) { id name } }')
    assert not result.errors
    assert result.data['users'] == [
        { 'id': '1', 'name': 'user1' },
        { 'id': '2', 'name': 'user2' },
    ]
    assert list(models.User.objects.values('id', 'name')) == [
        { 'id': 1, 'name': 'user1' },
        { 'id': 2, 'name': 'user2' },
    ]

def test_update(mutation, users):
    result = mutation('{ users: updateUsers(data: { name: "me" }, filters: ["id__lte=2"]) { id name } }')
    assert not result.errors
    assert result.data['users'] == [
        { 'id': '1', 'name': 'me' },
        { 'id': '2', 'name': 'me' },
    ]
    assert list(models.User.objects.values('id', 'name')) == [
        { 'id': 1, 'name': 'me' },
        { 'id': 2, 'name': 'me' },
        { 'id': 3, 'name': 'user3' },
    ]

def test_delete(mutation, users):
    result = mutation('{ ids: deleteUsers(filters: ["id__gt=1"]) }')
    assert not result.errors
    assert result.data['ids'] == [ '2', '3' ]
    assert list(models.User.objects.values('id', 'name')) == [
        { 'id': 1, 'name': 'user1' },
    ]

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async(schema):
    result = await schema.execute('mutation { user: createUser(data: { name: "user1" }) { id name } }')
    assert not result.errors
    assert result.data['user'] == { 'id': '1', 'name': 'user1' }
