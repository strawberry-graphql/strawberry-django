import pytest
import strawberry
import strawberry_django
from .. import models

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

    result = mutation('{ updateGroups(data: { tagsAdd: [1] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == [1]

    result = mutation('{ updateGroups(data: { tagsRemove: [1] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == []

    result = mutation('{ updateGroups(data: { tagsSet: [1] }) { id } }')
    assert not result.errors
    assert list(group.tags.values_list('id', flat=True)) == [1]
