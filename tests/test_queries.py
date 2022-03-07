from typing import List

import pytest
import strawberry

import strawberry_django
from strawberry_django import auto

from . import models, utils


@pytest.fixture
def user_group(users, groups):
    users[0].group = groups[0]
    users[0].save()


@strawberry_django.type(models.User)
class User:
    id: auto
    name: auto
    group: "Group"


@strawberry_django.type(models.Group)
class Group:
    id: auto
    name: auto
    users: List[User]


@strawberry_django.type(models.Fruit)
class BerryFruit:
    id: auto
    name: auto
    name_upper: str
    name_lower: str

    def get_queryset(self, queryset, info):
        return queryset.filter(name__contains="berry")


@strawberry_django.type(models.Fruit, is_interface=True)
class FruitInterface:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit)
class BananaFruit(FruitInterface):
    def get_queryset(self, queryset, info):
        return queryset.filter(name__contains="banana")


@strawberry.type
class Query:
    user: User = strawberry_django.field()
    users: List[User] = strawberry_django.field()
    group: Group = strawberry_django.field()
    groups: List[Group] = strawberry_django.field()
    berries: List[BerryFruit] = strawberry_django.field()
    bananas: List[BananaFruit] = strawberry_django.field()


@pytest.fixture
def query(db):
    return utils.generate_query(Query)


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.django_db(transaction=True),
]


async def test_single(query, users):
    result = await query("{ user(pk: 1) { name } }")

    assert not result.errors
    assert result.data["user"] == {"name": users[0].name}


async def test_many(query, users):
    result = await query("{ users { name } }")

    assert not result.errors
    assert result.data["users"] == [
        {"name": users[0].name},
        {"name": users[1].name},
        {"name": users[2].name},
    ]


async def test_relation(query, users, groups, user_group):
    result = await query("{ users { name group { name } } }")

    assert not result.errors
    assert result.data["users"] == [
        {"name": users[0].name, "group": {"name": groups[0].name}},
        {"name": users[1].name, "group": None},
        {"name": users[2].name, "group": None},
    ]


async def test_reverse_relation(query, users, groups, user_group):
    result = await query("{ groups { name users { name } } }")

    assert not result.errors
    assert result.data["groups"] == [
        {"name": groups[0].name, "users": [{"name": users[0].name}]},
        {"name": groups[1].name, "users": []},
        {"name": groups[2].name, "users": []},
    ]


async def test_type_queryset(query, fruits):
    result = await query("{ berries { name } }")

    assert not result.errors
    assert result.data["berries"] == [
        {"name": "strawberry"},
        {"name": "raspberry"},
    ]


async def test_querying_type_implementing_interface(query, fruits):
    result = await query("{ bananas { name } }")

    assert not result.errors
    assert result.data["bananas"] == [{"name": "banana"}]


async def test_model_properties(query, fruits):
    result = await query("{ berries { nameUpper nameLower } }")

    assert not result.errors
    assert result.data["berries"] == [
        {"nameUpper": "STRAWBERRY", "nameLower": "strawberry"},
        {"nameUpper": "RASPBERRY", "nameLower": "raspberry"},
    ]
