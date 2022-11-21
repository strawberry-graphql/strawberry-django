from typing import List

import pytest
import strawberry
from django.conf import settings

import strawberry_django

from . import models, types, utils


@pytest.fixture
def fruits(db):
    fruit_names = ["strawberry", "raspberry", "banana"]
    fruits = [models.Fruit.objects.create(name=name) for name in fruit_names]
    return fruits


@pytest.fixture
def tag(db):
    tag = models.Tag.objects.create(name="tag")
    return tag


@pytest.fixture
def group(db, tag):
    group = models.Group.objects.create(name="group")
    group.tags.add(tag)
    return group


@pytest.fixture
def user(db, group, tag):
    user = models.User.objects.create(name="user", group=group, tag=tag)
    return user


@pytest.fixture
def users(db):
    return [
        models.User.objects.create(name="user1"),
        models.User.objects.create(name="user2"),
        models.User.objects.create(name="user3"),
    ]


@pytest.fixture
def groups(db):
    return [
        models.Group.objects.create(name="group1"),
        models.Group.objects.create(name="group2"),
        models.Group.objects.create(name="group3"),
    ]


@pytest.fixture
def geofields(db):
    from django.contrib.gis.geos import (
        LineString,
        MultiLineString,
        MultiPoint,
        MultiPolygon,
        Point,
        Polygon,
    )

    return [
        models.GeosFieldsModel.objects.create(
            point=Point(x=0, y=0),
            line_string=LineString((0, 0), (1, 1)),
            polygon=Polygon(((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))),
            multi_point=MultiPoint(Point(x=0, y=0), Point(x=1, y=1)),
            multi_line_string=MultiLineString(
                LineString((0, 0), (1, 1)),
                LineString((1, 1), (-1, -1)),
            ),
            multi_polygon=MultiPolygon(
                Polygon(((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))),
                Polygon(((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))),
            ),
        ),
        models.GeosFieldsModel.objects.create(
            point=Point(x=1, y=1),
            line_string=LineString((1, 1), (2, 2), (3, 3)),
            polygon=Polygon(
                ((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)),
                ((-2, -2), (-2, 2), (2, 2), (2, -2), (-2, -2)),
            ),
            multi_point=MultiPoint(Point(x=0, y=0), Point(x=-1, y=-1), Point(x=1, y=1)),
            multi_line_string=MultiLineString(
                LineString((0, 0), (1, 1)),
                LineString((1, 1), (-1, -1)),
                LineString((2, 2), (-2, -2)),
            ),
            multi_polygon=MultiPolygon(
                Polygon(
                    ((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)),
                    ((-2, -2), (-2, 2), (2, 2), (2, -2), (-2, -2)),
                ),
                Polygon(
                    ((-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)),
                    ((-2, -2), (-2, 2), (2, 2), (2, -2), (-2, -2)),
                ),
            ),
        ),
    ]


@pytest.fixture
def schema():
    @strawberry.type
    class Query:
        user: types.User = strawberry_django.field()
        users: List[types.User] = strawberry_django.field()
        group: types.Group = strawberry_django.field()
        groups: List[types.Group] = strawberry_django.field()
        tag: types.Tag = strawberry_django.field()
        tags: List[types.Tag] = strawberry_django.field()

    @strawberry.type
    class GeoQuery(Query):
        geofield: types.GeoField = strawberry_django.field()
        geofields: List[types.GeoField] = strawberry_django.field()

    schema = strawberry.Schema(query=GeoQuery if settings.GEOS_IMPORTED else Query)
    return schema


@pytest.fixture(
    params=[
        strawberry_django.type,
        strawberry_django.input,
        utils.dataclass,
    ]
)
def testtype(request):
    return request.param
