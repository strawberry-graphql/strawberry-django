import pytest
import strawberry
from django.conf import settings
from django.test import override_settings
from strawberry import auto
from strawberry.types import get_object_definition

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import models, utils

pytestmark = pytest.mark.skipif(
    not settings.GEOS_IMPORTED, reason="GeoDjango is not available."
)

# Tests that expect the object type set it explicitly, so changing the default
# only affects `test_default_setting`
use_geometry_type = override_settings(STRAWBERRY_DJANGO={"USE_GEOMETRY_SCALARS": False})


def test_default_setting():
    from strawberry_django.settings import DEFAULT_DJANGO_SETTINGS

    assert DEFAULT_DJANGO_SETTINGS["USE_GEOMETRY_SCALARS"] is False


def _geometry_schema(geometry):
    @strawberry.type
    class Query:
        @strawberry.field
        def geometry(self) -> strawberry_django.DjangoGeometryType:
            return geometry

    return strawberry.Schema(query=Query)


@pytest.mark.django_db
@use_geometry_type
def test_geometry_type_output():
    from django.contrib.gis.geos import Point

    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        point: auto
        polygon: auto

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)
    models.GeosFieldsModel.objects.create(point=Point(1, 2))

    result = schema.execute_sync(
        "{ geos { point { wkt ewkt srid geomType geojson } polygon { wkt } } }"
    )

    assert not result.errors
    assert result.data is not None
    assert result.data == {
        "geos": [
            {
                "point": {
                    "wkt": "POINT (1 2)",
                    "ewkt": "SRID=4326;POINT (1 2)",
                    "srid": 4326,
                    "geomType": "Point",
                    "geojson": {"type": "Point", "coordinates": [1.0, 2.0]},
                },
                "polygon": None,
            }
        ]
    }


def test_geometry_type_geojson_is_transformed_to_4326():
    from django.contrib.gis.geos import GEOSGeometry

    # Seoul, in EPSG:3857
    schema = _geometry_schema(GEOSGeometry("SRID=3857;POINT(14135842.6 4518386.1)"))

    result = schema.execute_sync("{ geometry { srid ewkt geojson } }")

    assert not result.errors
    assert result.data is not None
    geometry = result.data["geometry"]
    assert geometry["srid"] == 3857
    assert geometry["ewkt"].startswith("SRID=3857;")
    assert geometry["geojson"]["type"] == "Point"
    # GeoJSON uses [longitude, latitude]
    assert geometry["geojson"]["coordinates"] == [
        pytest.approx(126.9844, abs=1e-4),
        pytest.approx(37.5666, abs=1e-4),
    ]


def test_geometry_type_geojson_without_srid():
    from django.contrib.gis.geos import GEOSGeometry

    schema = _geometry_schema(GEOSGeometry("POINT(1 2)"))

    result = schema.execute_sync("{ geometry { srid geojson } }")

    assert not result.errors
    assert result.data is not None
    assert result.data == {
        "geometry": {
            "srid": None,
            "geojson": {"type": "Point", "coordinates": [1.0, 2.0]},
        }
    }


@pytest.mark.django_db
@override_settings(STRAWBERRY_DJANGO={"USE_GEOMETRY_SCALARS": True})
def test_geometry_scalars_setting(geofields):
    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        point: auto
        line_string: auto
        polygon: auto
        multi_point: auto
        multi_line_string: auto
        multi_polygon: auto

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    result = schema.execute_sync(
        "{ geos { point lineString polygon multiPoint multiLineString multiPolygon } }"
    )

    assert not result.errors
    assert result.data is not None
    assert result.data["geos"] == [
        {
            "point": obj.point and obj.point.tuple,
            "lineString": obj.line_string and obj.line_string.tuple,
            "polygon": obj.polygon and obj.polygon.tuple,
            "multiPoint": obj.multi_point and obj.multi_point.tuple,
            "multiLineString": obj.multi_line_string and obj.multi_line_string.tuple,
            "multiPolygon": obj.multi_polygon and obj.multi_polygon.tuple,
        }
        for obj in geofields
    ]
    assert result.data["geos"][0]["point"] == (0.0, 0.0)


@use_geometry_type
def test_explicit_scalar_annotation_is_kept():
    from django.contrib.gis.geos import Polygon

    from strawberry_django.fields import types

    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        point: auto
        polygon: Polygon | None

    object_definition = get_object_definition(GeoType, strict=True)
    field_types = {f.name: f.type.of_type for f in object_definition.fields}  # type: ignore

    assert field_types == {
        "point": types.DjangoGeometryType,
        "polygon": Polygon,
    }


@pytest.mark.django_db(transaction=True)
@use_geometry_type
def test_input_inheriting_output_type_uses_scalars():
    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        id: auto
        point: auto
        polygon: auto

    @strawberry_django.input(models.GeosFieldsModel)
    class GeoInput(GeoType):
        pass

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    @strawberry.type
    class Mutation:
        create_geo: GeoType = strawberry_django.mutations.create(GeoInput)

    schema = strawberry.Schema(query=Query, mutation=Mutation)

    assert "point: Point" in str(schema)

    result = schema.execute_sync(
        'mutation { createGeo(data: { point: "POINT(1 2)", polygon: [[[0, 0], '
        "[0, 1], [1, 1], [0, 0]]] }) { point { wkt } polygon { geomType } } }"
    )

    assert not result.errors
    assert result.data is not None
    assert result.data == {
        "createGeo": {
            "point": {"wkt": "POINT (1 2)"},
            "polygon": {"geomType": "Polygon"},
        }
    }


@use_geometry_type
def test_filters_keep_geometry_lookups():
    @strawberry_django.filter_type(models.GeosFieldsModel, lookups=True)
    class GeoFilter:
        point: auto

    object_definition = get_object_definition(GeoFilter, strict=True)
    field_type = object_definition.get_field("point").type.of_type  # type: ignore

    assert field_type is strawberry_django.GeometryFilterLookup


@pytest.mark.django_db
@use_geometry_type
def test_geometry_type_with_optimizer(geofields):
    @strawberry_django.type(models.GeosFieldsModel)
    class GeoType:
        point: auto
        polygon: auto

    @strawberry.type
    class Query:
        geos: list[GeoType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    with utils.assert_num_queries(1) as ctx:
        result = schema.execute_sync("{ geos { point { wkt } } }")

    assert not result.errors
    assert result.data is not None
    assert len(result.data["geos"]) == len(geofields)
    # Only the selected geometry column is fetched
    sql = ctx.captured_queries[0]["sql"]
    assert '"point"' in sql
    assert '"polygon"' not in sql
