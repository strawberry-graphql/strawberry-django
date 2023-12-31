import textwrap
from typing import List, Optional, cast

import pytest
import strawberry
from django.test import override_settings
from graphql import GraphQLError
from strawberry import auto

import strawberry_django
from strawberry_django.settings import StrawberryDjangoSettings

from . import models, utils


@pytest.fixture()
def user_group(users, groups):  # noqa: PT004
    users[0].group = groups[0]
    users[0].save()


@strawberry_django.type(models.User)
class User:
    id: auto
    name: auto
    group: Optional["Group"]


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

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return queryset.filter(name__contains="berry")


@strawberry_django.type(models.Fruit, is_interface=True)
class FruitInterface:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit)
class BananaFruit(FruitInterface):
    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return queryset.filter(name__contains="banana")


@strawberry.type
class Query:
    user: User = strawberry_django.field()
    users: List[User] = strawberry_django.field()
    group: Group = strawberry_django.field()
    groups: List[Group] = strawberry_django.field()
    berries: List[BerryFruit] = strawberry_django.field()
    bananas: List[BananaFruit] = strawberry_django.field()


@pytest.fixture()
def query(db):
    return utils.generate_query(Query)


@pytest.fixture()
def query_id_as_pk(db):
    with override_settings(
        STRAWBERRY_DJANGO=StrawberryDjangoSettings(
            DEFAULT_PK_FIELD_NAME="id",
        ),
    ):
        yield utils.generate_query(Query)


pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_single(query, users):
    result = await query("{ user(pk: 1) { name } }")

    assert not result.errors
    assert result.data["user"] == {"name": users[0].name}


async def test_required_pk_single(query, users):
    result = await query("{ user { name } }")

    assert bool(result.errors)
    assert len(result.errors) == 1
    assert isinstance(result.errors[0], GraphQLError)
    assert (
        result.errors[0].message == "Field 'user' argument 'pk' of type 'ID!' is "
        "required, but it was not provided."
    )


async def test_id_as_pk_single(query_id_as_pk, users):
    # Users are created for each test, it's impossible to know what will be the id of users in the database.
    user_id = users[0].id
    result = await query_id_as_pk(f"{{ user(id: {user_id}) {{ name }} }}")

    assert not result.errors
    assert result.data["user"] == {"name": users[0].name}


async def test_required_id_as_pk_single(query_id_as_pk, users):
    result = await query_id_as_pk("{ user { name } }")

    assert bool(result.errors)
    assert len(result.errors) == 1
    assert isinstance(result.errors[0], GraphQLError)
    assert (
        result.errors[0].message == "Field 'user' argument 'id' of type 'ID!' is "
        "required, but it was not provided."
    )


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


def test_field_name():
    """Make sure that field_name overriding is not ignored."""

    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: auto
        color_id: int = strawberry_django.field(field_name="color_id")

    @strawberry.type
    class Query:
        @strawberry_django.field
        def fruit(self) -> Fruit:
            color = models.Color.objects.create(name="Yellow")
            return cast(
                Fruit,
                models.Fruit.objects.create(
                    name="Banana",
                    color=color,
                ),
            )

    schema = strawberry.Schema(query=Query)
    expected = """\
      type Fruit {
        name: String!
        colorId: Int!
      }

      type Query {
        fruit: Fruit!
      }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        """\
      query TestQuery {
        fruit {
          name
          colorId
        }
      }
    """
    )
    assert result.data == {"fruit": {"colorId": 1, "name": "Banana"}}
