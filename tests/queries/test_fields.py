from typing import List

import pytest
import strawberry
from django.conf import settings

import strawberry_django

from .. import models, types, utils


def generate_query(UserType):
    @strawberry.type
    class Query:
        users: List[UserType] = strawberry_django.field()

    return utils.generate_query(Query)


def test_field_name(user):
    @strawberry_django.type(models.User)
    class User:
        my_name: str = strawberry_django.field(field_name="name")

    query = generate_query(User)

    result = query("{ users { myName } }")
    assert not result.errors
    assert result.data["users"] == [{"myName": "user"}]


def test_relational_field_name(user, group):
    @strawberry_django.type(models.User)
    class User:
        my_group: types.Group = strawberry_django.field(field_name="group")

    query = generate_query(User)

    result = query("{ users { myGroup { name } } }")
    assert not result.errors
    assert result.data["users"] == [{"myGroup": {"name": "group"}}]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_sync_resolver(user, group):
    @strawberry_django.type(models.User)
    class User:
        @strawberry_django.field
        def my_group(self, info) -> types.Group:
            return models.Group.objects.get()

    query = generate_query(User)

    result = await query("{ users { myGroup { name } } }")
    assert not result.errors
    assert result.data["users"] == [{"myGroup": {"name": "group"}}]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_resolver(user, group):
    @strawberry_django.type(models.User)
    class User:
        @strawberry_django.field
        async def my_group(self, info) -> types.Group:
            from asgiref.sync import sync_to_async

            return await sync_to_async(models.Group.objects.get)()

    query = generate_query(User)

    result = await query("{ users { myGroup { name } } }")
    assert not result.errors
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
    ]

    # Test fo lineString
    result = query("{ geofields { lineString } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"lineString": ((0.0, 0.0), (1.0, 1.0))},
        {"lineString": ((1.0, 1.0), (2.0, 2.0), (3.0, 3.0))},
    ]

    # Test for polygon
    result = query("{ geofields { polygon } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {
            "polygon": (
                ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
            )
        },
        {
            "polygon": (
                ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
            )
        },
    ]

    # Test for multiPoint
    result = query("{ geofields { multiPoint } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"multiPoint": ((0.0, 0.0), (1.0, 1.0))},
        {"multiPoint": ((0.0, 0.0), (-1.0, -1.0), (1.0, 1.0))},
    ]

    # Test for multiLineString
    result = query("{ geofields { multiLineString } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {"multiLineString": [((0.0, 0.0), (1.0, 1.0)), ((1.0, 1.0), (-1.0, -1.0))]},
        {
            "multiLineString": [
                ((0.0, 0.0), (1.0, 1.0)),
                ((1.0, 1.0), (-1.0, -1.0)),
                ((2.0, 2.0), (-2.0, -2.0)),
            ]
        },
    ]

    # Test for multiPolygon
    result = query("{ geofields { multiPolygon } }")
    assert not result.errors

    assert result.data["geofields"] == [
        {
            "multiPolygon": [
                ((((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0))),),
                ((((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0))),),
            ]
        },
        {
            "multiPolygon": [
                (
                    ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                    ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
                ),
                (
                    ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
                    ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
                ),
            ]
        },
    ]
