import textwrap
from typing import Optional, cast

import pytest
import strawberry
from django.conf import settings
from strawberry.types import ExecutionResult

import strawberry_django
from tests import models, types, utils


def generate_query(user_type):
    @strawberry.type
    class Query:
        users: list[user_type] = strawberry_django.field()  # type: ignore

    return utils.generate_query(Query)


def test_field_name(user):
    @strawberry_django.type(models.User)
    class MyUser:
        my_name: str = strawberry_django.field(field_name="name")

    query = generate_query(MyUser)

    result = query("{ users { myName } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"myName": "user"}]


def test_relational_field_name(user, group):
    @strawberry_django.type(models.User)
    class MyUser:
        my_group: types.Group = strawberry_django.field(field_name="group")

    query = generate_query(MyUser)

    result = query("{ users { myGroup { name } } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"myGroup": {"name": "group"}}]


def test_foreign_key_id_with_auto(group, user):
    @strawberry_django.type(models.User)
    class MyUser:
        group_id: strawberry.auto

    @strawberry.type
    class Query:
        users: list[MyUser] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    expected = """\
    type MyUser {
      groupId: ID
    }

    type Query {
      users: [MyUser!]!
    }
    """
    assert textwrap.dedent(str(schema)).strip() == textwrap.dedent(expected).strip()

    result = schema.execute_sync("{ users { groupId } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"groupId": str(group.id)}]


def test_foreign_key_id_with_explicit_type(group, user):
    @strawberry_django.type(models.User)
    class MyUser:
        group_id: Optional[strawberry.ID]

    @strawberry.type
    class Query:
        users: list[MyUser] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    expected = """\
    type MyUser {
      groupId: ID
    }

    type Query {
      users: [MyUser!]!
    }
    """
    assert textwrap.dedent(str(schema)).strip() == textwrap.dedent(expected).strip()

    result = schema.execute_sync("{ users { groupId } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"groupId": str(group.id)}]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_sync_resolver(user, group):
    @strawberry_django.type(models.User)
    class MyUser:
        @strawberry_django.field
        def my_group(self, info) -> types.Group:
            return cast(types.Group, models.Group.objects.get())

    query = generate_query(MyUser)

    result = await query("{ users { myGroup { name } } }")  # type: ignore
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"myGroup": {"name": "group"}}]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_resolver(user, group):
    @strawberry_django.type(models.User)
    class MyUser:
        @strawberry_django.field
        async def my_group(self, info) -> types.Group:
            from asgiref.sync import sync_to_async

            return cast(types.Group, await sync_to_async(models.Group.objects.get)())

    query = generate_query(MyUser)

    result = await query("{ users { myGroup { name } } }")  # type: ignore
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["users"] == [{"myGroup": {"name": "group"}}]


@pytest.mark.skipif(
    not settings.GEOS_IMPORTED,
    reason="Test requires GEOS to be imported and properly configured",
)
@pytest.mark.django_db(transaction=True)
def test_geo_data(query, geofields):
    # Test for point
    result = query("{ geofields { point } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"point": (0.0, 0.0)},
        {"point": (1.0, 1.0)},
        {"point": None},
    ]

    # Test for lineString
    result = query("{ geofields { lineString } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"lineString": ((0.0, 0.0), (1.0, 1.0))},
        {"lineString": ((1.0, 1.0), (2.0, 2.0), (3.0, 3.0))},
        {"lineString": None},
    ]

    # Test for polygon
    result = query("{ geofields { polygon } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {
            "polygon": (
                ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
            ),
        },
        {
            "polygon": (
                ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
            ),
        },
        {"polygon": None},
    ]

    # Test for multiPoint
    result = query("{ geofields { multiPoint } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"multiPoint": ((0.0, 0.0), (1.0, 1.0))},
        {"multiPoint": ((0.0, 0.0), (-1.0, -1.0), (1.0, 1.0))},
        {"multiPoint": None},
    ]

    # Test for multiLineString
    result = query("{ geofields { multiLineString } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"multiLineString": (((0.0, 0.0), (1.0, 1.0)), ((1.0, 1.0), (-1.0, -1.0)))},
        {
            "multiLineString": (
                ((0.0, 0.0), (1.0, 1.0)),
                ((1.0, 1.0), (-1.0, -1.0)),
                ((2.0, 2.0), (-2.0, -2.0)),
            ),
        },
        {"multiLineString": None},
    ]

    # Test for multiPolygon
    result = query("{ geofields { multiPolygon } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {
            "multiPolygon": (
                ((((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0))),),
                ((((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0))),),
            ),
        },
        {
            "multiPolygon": (
                (
                    ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                    ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
                ),
                (
                    ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                    ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
                ),
            ),
        },
        {"multiPolygon": None},
    ]
