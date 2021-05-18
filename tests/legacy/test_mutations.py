import pytest
import strawberry
import strawberry_django
from . import models, types
from .. import utils


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
async def test_async(mutation):
    result = await mutation('{ user: createUser(data: { name: "user1" }) { name } }')
    assert not result.errors
    assert result.data['user'] == { 'name': 'user1' }


def test_create_foreign_key(mutation, group):
    result = mutation('{ createUser(data: { name: "user", groupId: 1 }) { id } }')
    assert not result.errors
    user = models.User.objects.get()
    assert user.group == group


def test_create_many_to_many(mutation, tag):
    result = mutation('{ createGroup(data: { name: "group", tagsSet: [1] }) { id } }')
    assert not result.errors
    group = models.Group.objects.get()
    assert list(group.tags.values_list('id', flat=True)) == [1]


def test_update_foreign_key(mutation, user, group):
    result = mutation('{ updateUsers(data: { groupId: 1 }) { id } }')
    assert not result.errors
    user = models.User.objects.get()
    assert user.group == group

    result = mutation('{ updateUsers(data: { name: "newName" }) { id } }')
    assert not result.errors
    user = models.User.objects.get()
    assert user.group == group

    result = mutation('{ updateUsers(data: { groupId: null }) { id } }')
    assert not result.errors
    user = models.User.objects.get()
    assert user.group == None


def test_update_many_to_many(mutation, group, tag):
    group = models.Group.objects.get()
    group.tags.clear()
    tag2 = models.Tag.objects.create(name='tag2')

    result = mutation('{ updateGroups(data: { tagsAdd: [1, 2] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == [1, 2]

    result = mutation('{ updateGroups(data: { tagsRemove: [1, 2] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == []

    result = mutation('{ updateGroups(data: { tagsSet: [1, 2] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == [1, 2]


def test_save_hooks(db):
    def hook(info, instance):
        hook.data.append(instance.id)
    hook.data = []

    @strawberry.type
    class Mutation:
        create_user = strawberry_django.mutations.create(models.User, types.User, types.UserInput, pre_save=hook)
        create_user.post_save(hook)
    mutation = utils.generate_query(mutation=Mutation)

    result = mutation('{ user: createUser(data: { name: "user" }) { id } }')
    assert not result.errors
    assert result.data['user'] == { 'id': '1' }
    assert hook.data == [ None, 1 ]
