import math

import pytest
import strawberry
from asgiref.sync import sync_to_async
from django.conf import settings
from django.test import override_settings
from strawberry import auto

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import models, utils

pytestmark = pytest.mark.skipif(
    not settings.GEOS_IMPORTED, reason="GeoDjango is not available."
)

use_geometry_type = override_settings(STRAWBERRY_DJANGO={"USE_GEOMETRY_SCALARS": False})


def _circle(vertices=2000):
    from django.contrib.gis.geos import Polygon

    points = [
        (
            126.98 + 0.1 * math.cos(2 * math.pi * i / vertices),
            37.57 + 0.1 * math.sin(2 * math.pi * i / vertices),
        )
        for i in range(vertices)
    ]
    return Polygon([*points, points[0]], srid=4326)


def _schema(*, optimizer=False):
    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        point: auto
        polygon: auto

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    return strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension] if optimizer else [],
    )


def _arguments(schema, type_name, field_name):
    field = schema.get_type_by_name(type_name).fields
    return [
        arg.python_name
        for f in field
        if f.python_name == field_name
        for arg in f.arguments
    ]


@use_geometry_type
def test_simplify_argument_only_on_geometry_object_fields():
    from django.contrib.gis.geos import Polygon

    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        id: auto
        point: auto
        polygon: Polygon | None

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    assert _arguments(schema, "GeoType", "point") == ["simplify"]
    # Explicit scalar annotations and other fields don't get it
    assert _arguments(schema, "GeoType", "polygon") == []
    assert _arguments(schema, "GeoType", "id") == []


@override_settings(STRAWBERRY_DJANGO={"USE_GEOMETRY_SCALARS": True})
def test_simplify_argument_not_available_with_geometry_scalars():
    schema = _schema()

    assert _arguments(schema, "GeoType", "polygon") == []


@pytest.mark.django_db
@use_geometry_type
def test_simplify():
    polygon = _circle()
    models.GeosFieldsModel.objects.create(polygon=polygon)
    expected = polygon.simplify(0.001, preserve_topology=True)

    result = _schema().execute_sync(
        "{ geos { polygon(simplify: { tolerance: 0.001 }) { wkt ewkt geojson } } }"
    )

    assert not result.errors
    assert result.data is not None
    output = result.data["geos"][0]["polygon"]
    assert output["wkt"] == expected.wkt
    assert output["ewkt"] == f"SRID=4326;{expected.wkt}"
    # Every representation describes the same simplified geometry
    assert len(output["geojson"]["coordinates"][0]) == expected.num_points
    assert expected.num_points < polygon.num_points / 10


@pytest.mark.django_db
@use_geometry_type
def test_no_simplify_by_default():
    polygon = _circle()
    models.GeosFieldsModel.objects.create(polygon=polygon)

    result = _schema().execute_sync("{ geos { polygon { geojson } } }")

    assert not result.errors
    assert result.data is not None
    coordinates = result.data["geos"][0]["polygon"]["geojson"]["coordinates"][0]
    assert len(coordinates) == polygon.num_points


@pytest.mark.django_db
@use_geometry_type
def test_simplify_preserve_topology():
    models.GeosFieldsModel.objects.create(polygon=_circle())
    schema = _schema()

    result = schema.execute_sync(
        "{ geos { polygon(simplify: { tolerance: 1 }) { geomType wkt } } }"
    )
    assert not result.errors
    assert result.data is not None
    assert result.data["geos"][0]["polygon"]["geomType"] == "Polygon"
    assert result.data["geos"][0]["polygon"]["wkt"] != "POLYGON EMPTY"

    # Without preserving the topology, the polygon collapses
    result = schema.execute_sync(
        "{ geos { polygon(simplify: { tolerance: 1, preserveTopology: false }) "
        "{ wkt } } }"
    )
    assert not result.errors
    assert result.data is not None
    assert result.data["geos"][0]["polygon"]["wkt"] == "POLYGON EMPTY"


@pytest.mark.django_db
@use_geometry_type
def test_simplify_null_geometry():
    models.GeosFieldsModel.objects.create()

    result = _schema().execute_sync(
        "{ geos { polygon(simplify: { tolerance: 0.001 }) { wkt } } }"
    )

    assert not result.errors
    assert result.data == {"geos": [{"polygon": None}]}


@pytest.mark.django_db
@use_geometry_type
def test_simplify_negative_tolerance():
    models.GeosFieldsModel.objects.create(polygon=_circle())

    result = _schema().execute_sync(
        "{ geos { polygon(simplify: { tolerance: -1 }) { wkt } } }"
    )

    assert result.errors
    assert "`tolerance` must be greater than or equal to 0" in result.errors[0].message


@pytest.mark.django_db
@use_geometry_type
def test_simplify_with_optimizer():
    models.GeosFieldsModel.objects.create(polygon=_circle(), point="POINT(1 2)")

    with utils.assert_num_queries(1) as ctx:
        result = _schema(optimizer=True).execute_sync(
            "{ geos { polygon(simplify: { tolerance: 0.001 }) { geomType } } }"
        )

    assert not result.errors
    assert result.data == {"geos": [{"polygon": {"geomType": "Polygon"}}]}
    # Only the selected geometry column is fetched
    sql = ctx.captured_queries[0]["sql"]
    assert '"polygon"' in sql
    assert '"point"' not in sql


@pytest.mark.django_db(transaction=True)
@use_geometry_type
@pytest.mark.parametrize("deferred", [False, True])
async def test_simplify_async(deferred):
    polygon = _circle()
    await sync_to_async(models.GeosFieldsModel.objects.create)(polygon=polygon)
    expected = polygon.simplify(0.001, preserve_topology=True)

    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        polygon: auto

        @classmethod
        def get_queryset(cls, queryset, info, **kwargs):
            # A deferred column is fetched when resolving the field, which makes
            # the result awaitable
            return queryset.defer("polygon") if deferred else queryset

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    result = await strawberry.Schema(query=Query).execute(
        "{ geos { polygon(simplify: { tolerance: 0.001 }) { wkt } } }"
    )

    assert not result.errors
    assert result.data == {"geos": [{"polygon": {"wkt": expected.wkt}}]}
