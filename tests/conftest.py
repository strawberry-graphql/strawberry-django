import contextlib
import pathlib
import shutil
from typing import Dict, List, Tuple, Type, Union, cast

import pytest
import strawberry
from django.conf import settings
from django.test.client import (
    AsyncClient,  # type: ignore
    Client,
)

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests.utils import GraphQLTestClient

from . import models, types, utils

_TESTS_DIR = pathlib.Path(__file__).parent
_ROOT_DIR = _TESTS_DIR.parent


@pytest.fixture(scope="session", autouse=True)
def _cleanup(request):
    def cleanup_function():
        shutil.rmtree(_ROOT_DIR / ".tmp_upload", ignore_errors=True)

    request.addfinalizer(cleanup_function)  # noqa: PT021


@pytest.fixture(params=["sync", "async", "sync_no_optimizer", "async_no_optimizer"])
def gql_client(request):
    client, path, with_optimizer = cast(
        Dict[str, Tuple[Union[Type[Client], Type[AsyncClient]], str, bool]],
        {
            "sync": (Client, "/graphql/", True),
            "async": (AsyncClient, "/graphql_async/", True),
            "sync_no_optimizer": (Client, "/graphql/", False),
            "async_no_optimizer": (AsyncClient, "/graphql_async/", False),
        },
    )[request.param]

    if with_optimizer:
        optimizer_ctx = contextlib.nullcontext
    else:
        optimizer_ctx = DjangoOptimizerExtension.disabled

    with optimizer_ctx(), GraphQLTestClient(path, client()) as c:
        yield c


@pytest.fixture
def fruits(db):
    fruit_names = ["strawberry", "raspberry", "banana"]
    return [models.Fruit.objects.create(name=name) for name in fruit_names]


@pytest.fixture
def vegetables(db):
    vegetable_names = ["carrot", "cucumber", "onion"]
    vegetable_world_production = [40.0e6, 75.2e6, 102.2e6]  # in tons
    return [
        models.Vegetable.objects.create(name=n, world_production=p)
        for n, p in zip(vegetable_names, vegetable_world_production)
    ]


@pytest.fixture
def tag(db):
    return models.Tag.objects.create(name="tag")


@pytest.fixture
def group(db, tag):
    group = models.Group.objects.create(name="group")
    group.tags.add(tag)
    return group


@pytest.fixture
def user(db, group, tag):
    return models.User.objects.create(name="user", group=group, tag=tag)


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


if settings.GEOS_IMPORTED:

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
                multi_point=MultiPoint(
                    Point(x=0, y=0),
                    Point(x=-1, y=-1),
                    Point(x=1, y=1),
                ),
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
            models.GeosFieldsModel.objects.create(),
        ]


@pytest.fixture(params=["optimizer_enabled", "optimizer_disabled"])
def schema(request):
    @strawberry.type
    class Query:
        user: types.User = strawberry_django.field()
        users: List[types.User] = strawberry_django.field()
        group: types.Group = strawberry_django.field()
        groups: List[types.Group] = strawberry_django.field()
        tag: types.Tag = strawberry_django.field()
        tags: List[types.Tag] = strawberry_django.field()

    if request.param == "optimizer_enabled":
        extensions = [DjangoOptimizerExtension()]
    elif request.param == "optimizer_disabled":
        extensions = []
    else:
        raise AssertionError(f"Not able to handle param '{request.param}'")

    if settings.GEOS_IMPORTED:

        @strawberry.type
        class GeoQuery(Query):
            geofields: List[types.GeoField] = strawberry_django.field()

        return strawberry.Schema(query=GeoQuery, extensions=extensions)

    return strawberry.Schema(query=Query, extensions=extensions)


@pytest.fixture(
    params=[
        strawberry_django.type,
        strawberry_django.input,
        utils.dataclass,
    ],
)
def testtype(request):
    return request.param
