import pytest
import strawberry
from django.conf import settings

pytestmark = pytest.mark.skipif(
    not settings.GEOS_IMPORTED, reason="GeoDjango is not available."
)

if settings.GEOS_IMPORTED:
    from django.contrib.gis import geos

    import strawberry_django  # noqa: F401  # registers the geos scalars

    @strawberry.type
    class Query:
        @strawberry.field
        def point(self, value: geos.Point) -> str:
            return value.ewkt

        @strawberry.field
        def line_string(self, value: geos.LineString) -> str:
            return value.ewkt

        @strawberry.field
        def linear_ring(self, value: geos.LinearRing) -> str:
            return value.ewkt

        @strawberry.field
        def polygon(self, value: geos.Polygon) -> str:
            return value.ewkt

        @strawberry.field
        def multi_point(self, value: geos.MultiPoint) -> str:
            return value.ewkt

        @strawberry.field
        def multi_line_string(self, value: geos.MultiLineString) -> str:
            return value.ewkt

        @strawberry.field
        def multi_polygon(self, value: geos.MultiPolygon) -> str:
            return value.ewkt

        @strawberry.field
        def geometry(self, value: geos.GEOSGeometry) -> str:
            return value.ewkt


@pytest.fixture
def schema():
    return strawberry.Schema(query=Query)


def _query_variable(schema, field, scalar, value):
    return schema.execute_sync(
        f"query ($value: {scalar}!) {{ {field}(value: $value) }}",
        variable_values={"value": value},
    )


POINT_WKT = "POINT (1 2)"
POLYGON_COORDS = [[[0, 0], [0, 1], [1, 1], [0, 0]]]
POLYGON_WKT = "POLYGON ((0 0, 0 1, 1 1, 0 0))"


@pytest.mark.parametrize(
    ("field", "scalar", "value", "expected"),
    [
        # Coordinates keep working
        ("point", "Point", [1, 2], POINT_WKT),
        ("polygon", "Polygon", POLYGON_COORDS, POLYGON_WKT),
        # WKT, EWKT and HEXEWKB
        ("point", "Point", "POINT(1 2)", POINT_WKT),
        ("point", "Point", "SRID=3857;POINT(1 2)", f"SRID=3857;{POINT_WKT}"),
        ("point", "Point", "0101000000000000000000F03F0000000000000040", POINT_WKT),
        # GeoJSON defaults to SRID 4326
        (
            "point",
            "Point",
            '{"type": "Point", "coordinates": [1, 2]}',
            f"SRID=4326;{POINT_WKT}",
        ),
        (
            "point",
            "Point",
            {"type": "Point", "coordinates": [1, 2]},
            f"SRID=4326;{POINT_WKT}",
        ),
        ("lineString", "LineString", "LINESTRING(0 0, 1 1)", "LINESTRING (0 0, 1 1)"),
        (
            "linearRing",
            "LinearRing",
            "LINEARRING(0 0, 0 1, 1 1, 0 0)",
            "LINEARRING (0 0, 0 1, 1 1, 0 0)",
        ),
        (
            "polygon",
            "Polygon",
            {"type": "Polygon", "coordinates": POLYGON_COORDS},
            f"SRID=4326;{POLYGON_WKT}",
        ),
        (
            "multiPoint",
            "MultiPoint",
            "MULTIPOINT(0 0, 1 1)",
            "MULTIPOINT ((0 0), (1 1))",
        ),
        (
            "multiLineString",
            "MultiLineString",
            "MULTILINESTRING((0 0, 1 1), (1 1, 2 2))",
            "MULTILINESTRING ((0 0, 1 1), (1 1, 2 2))",
        ),
        (
            "multiPolygon",
            "MultiPolygon",
            {"type": "MultiPolygon", "coordinates": [POLYGON_COORDS]},
            "SRID=4326;MULTIPOLYGON (((0 0, 0 1, 1 1, 0 0)))",
        ),
        ("geometry", "Geometry", "POINT(1 2)", POINT_WKT),
        (
            "geometry",
            "Geometry",
            {"type": "Polygon", "coordinates": POLYGON_COORDS},
            f"SRID=4326;{POLYGON_WKT}",
        ),
    ],
)
def test_geos_scalar_input(schema, field, scalar, value, expected):
    result = _query_variable(schema, field, scalar, value)

    assert not result.errors
    assert result.data == {field: expected}


@pytest.mark.parametrize(
    ("field", "scalar", "value", "error"),
    [
        (
            "point",
            "Point",
            "POLYGON((0 0, 0 1, 1 1, 0 0))",
            "Expected a Point geometry",
        ),
        (
            "polygon",
            "Polygon",
            {"type": "Point", "coordinates": [1, 2]},
            "Expected a Polygon geometry",
        ),
        ("geometry", "Geometry", [1, 2], "Expected WKT, EWKT, HEXEWKB or GeoJSON"),
        ("point", "Point", "not a geometry", "Expected type 'Point'"),
        (
            "geometry",
            "Geometry",
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1, 2]},
                "properties": {},
            },
            "Expected type 'Geometry'",
        ),
    ],
)
def test_geos_scalar_invalid_input(schema, field, scalar, value, error):
    result = _query_variable(schema, field, scalar, value)

    assert result.errors
    assert error in result.errors[0].message


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("[1, 2]", POINT_WKT),
        ('"POINT(1 2)"', POINT_WKT),
        ('{type: "Point", coordinates: [1, 2]}', f"SRID=4326;{POINT_WKT}"),
    ],
)
def test_geos_scalar_inline_literal(schema, literal, expected):
    result = schema.execute_sync(f"{{ point(value: {literal}) }}")

    assert not result.errors
    assert result.data == {"point": expected}
