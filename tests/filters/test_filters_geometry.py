import pytest
import strawberry
from django.conf import settings
from strawberry import auto
from strawberry.types import get_object_definition

import strawberry_django
from tests import models, utils

pytestmark = pytest.mark.skipif(
    not settings.GEOS_IMPORTED, reason="GeoDjango is not available."
)

if settings.GEOS_IMPORTED:

    @strawberry_django.filter_type(models.GeosFieldsModel, lookups=True)
    class GeoFieldFilter:
        point: auto
        polygon: auto
        geometry: auto

    @strawberry_django.type(models.GeosFieldsModel, filters=GeoFieldFilter)
    class GeoFieldType:
        id: auto

    @strawberry.type
    class Query:
        geos: list[GeoFieldType] = strawberry_django.field()


SQUARE = "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"


@pytest.fixture
def query():
    return utils.generate_query(Query)


@pytest.fixture
def geos_objs(db):
    from django.contrib.gis.geos import GEOSGeometry

    return {
        "inside": models.GeosFieldsModel.objects.create(
            point=GEOSGeometry("POINT(5 5)"),
            polygon=GEOSGeometry(SQUARE),
            geometry=GEOSGeometry("POINT(5 5)"),
        ),
        "edge": models.GeosFieldsModel.objects.create(
            point=GEOSGeometry("POINT(10 5)"),
            polygon=GEOSGeometry("POLYGON((10 0, 10 10, 20 10, 20 0, 10 0))"),
            geometry=GEOSGeometry("LINESTRING(10 0, 20 10)"),
        ),
        "overlapping": models.GeosFieldsModel.objects.create(
            point=GEOSGeometry("POINT(50 50)"),
            polygon=GEOSGeometry("POLYGON((5 5, 5 15, 15 15, 15 5, 5 5))"),
            geometry=GEOSGeometry("LINESTRING(5 5, 15 15)"),
        ),
        "far": models.GeosFieldsModel.objects.create(
            polygon=GEOSGeometry(
                "POLYGON((100 100, 100 110, 110 110, 110 100, 100 100))"
            ),
            geometry=GEOSGeometry(SQUARE),
        ),
    }


def test_geometry_filter_lookup_type():
    filter_def = get_object_definition(GeoFieldFilter, strict=True)
    for field_name in ("point", "polygon", "geometry"):
        field_type = filter_def.get_field(field_name).type.of_type  # type: ignore
        assert field_type is strawberry_django.GeometryFilterLookup

    lookup_def = get_object_definition(
        strawberry_django.GeometryFilterLookup, strict=True
    )
    assert {f.name for f in lookup_def.fields} == {
        "exact",
        "is_null",
        "contains",
        "disjoint",
        "equals",
        "intersects",
        "overlaps",
        "touches",
        "within",
    }


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"polygon": {"exact": SQUARE}}, ["inside"]),
        ({"polygon": {"contains": SQUARE}}, ["inside"]),
        ({"polygon": {"disjoint": SQUARE}}, ["far"]),
        ({"polygon": {"equals": SQUARE}}, ["inside"]),
        ({"polygon": {"intersects": SQUARE}}, ["inside", "edge", "overlapping"]),
        ({"polygon": {"overlaps": SQUARE}}, ["overlapping"]),
        ({"polygon": {"touches": SQUARE}}, ["edge"]),
        ({"polygon": {"within": SQUARE}}, ["inside"]),
        ({"point": {"within": SQUARE}}, ["inside"]),
        ({"point": {"intersects": SQUARE}}, ["inside", "edge"]),
        ({"point": {"touches": SQUARE}}, ["edge"]),
        ({"point": {"isNull": True}}, ["far"]),
        ({"geometry": {"within": SQUARE}}, ["inside", "far"]),
        ({"geometry": {"crosses": SQUARE}}, None),
        ({"point": {"inList": ["POINT(5 5)"]}}, None),
    ],
)
def test_geometry_filter_lookups(query, geos_objs, filters, expected):
    result = query(
        """
        query GeosQuery($filters: GeoFieldFilter) {
          geos(filters: $filters) {
            id
          }
        }
        """,
        {"filters": filters},
    )

    if expected is None:
        # Lookups that don't work on every backend are not exposed
        assert result.errors
        return

    assert not result.errors
    assert sorted(int(r["id"]) for r in result.data["geos"]) == sorted(
        geos_objs[name].pk for name in expected
    )
