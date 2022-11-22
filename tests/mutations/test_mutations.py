import pytest
from django.conf import settings

from tests import models
from tests.utils import deep_tuple_to_list


def test_create(mutation):
    result = mutation(
        '{ fruit: createFruit(data: { name: "strawberry" }) { id name } }'
    )
    assert not result.errors
    assert result.data["fruit"] == {"id": "1", "name": "strawberry"}
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "strawberry"},
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_create_async(mutation):
    result = await mutation(
        '{ fruit: createFruit(data: { name: "strawberry" }) { name } }'
    )
    assert not result.errors
    assert result.data["fruit"] == {"name": "strawberry"}


def test_create_many(mutation):
    result = mutation(
        '{ fruits: createFruits(data: [{ name: "strawberry" },'
        ' { name: "raspberry" }]) { id name } }'
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
    ]
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "strawberry"},
        {"id": 2, "name": "raspberry"},
    ]


def test_update(mutation, fruits):
    result = mutation('{ fruits: updateFruits(data: { name: "orange" }) { id name } }')
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "orange"},
        {"id": "2", "name": "orange"},
        {"id": "3", "name": "orange"},
    ]
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "orange"},
        {"id": 2, "name": "orange"},
        {"id": 3, "name": "orange"},
    ]


def test_update_with_filters(mutation, fruits):
    result = mutation(
        '{ fruits: updateFruits(data: { name: "orange" },'
        " filters: { id: { inList: [1, 2] } } ) { id name } }"
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "orange"},
        {"id": "2", "name": "orange"},
    ]
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "orange"},
        {"id": 2, "name": "orange"},
        {"id": 3, "name": "banana"},
    ]


def test_delete(mutation, fruits):
    result = mutation("{ fruits: deleteFruits { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
        {"id": "3", "name": "banana"},
    ]
    assert list(models.Fruit.objects.values("id", "name")) == []


def test_delete_with_filters(mutation, fruits):
    result = mutation(
        '{ fruits: deleteFruits(filters: { name: { contains: "berry" } }) { id name } }'
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
    ]
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 3, "name": "banana"},
    ]


@pytest.mark.skipif(
    not settings.GEOS_IMPORTED,
    reason="Test requires GEOS to be imported and properly configured",
)
@pytest.mark.django_db(transaction=True)
def test_create_geo(mutation):
    from tests.models import GeosFieldsModel

    # Test for point
    point = [0.0, 1.0]
    result = mutation(
        "{ geofield: createGeoField(data: { point: " + str(point) + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).point.tuple
        )
        == point
    )

    # Test for lineString
    line_string = [[0.0, 0.0], [1.0, 1.0]]
    result = mutation(
        "{ geofield: createGeoField(data: { lineString: "
        + str(line_string)
        + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(
                id=result.data["geofield"]["id"]
            ).line_string.tuple
        )
        == line_string
    )

    # Test for polygon
    polygon = [
        [[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0], [-1.0, -1.0]],
        [[-2.0, -2.0], [-2.0, 2.0], [2.0, 2.0], [2.0, -2.0], [-2.0, -2.0]],
    ]
    result = mutation(
        "{ geofield: createGeoField(data: { polygon: " + str(polygon) + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).polygon.tuple
        )
        == polygon
    )

    # Test for multi_point
    multi_point = [[0.0, 0.0], [-1.0, -1.0], [1.0, 1.0]]
    result = mutation(
        "{ geofield: createGeoField(data: { multiPoint: "
        + str(multi_point)
        + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(
                id=result.data["geofield"]["id"]
            ).multi_point.tuple
        )
        == multi_point
    )

    # Test for multiLineString
    multi_line_string = [
        [[0.0, 0.0], [1.0, 1.0]],
        [[1.0, 1.0], [-1.0, -1.0]],
        [[2.0, 2.0], [-2.0, -2.0]],
    ]
    result = mutation(
        "{ geofield: createGeoField(data: { multiLineString: "
        + str(multi_line_string)
        + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(
                id=result.data["geofield"]["id"]
            ).multi_line_string.tuple
        )
        == multi_line_string
    )

    # Test for multiPolygon
    multi_polygon = [
        [
            [[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0], [-1.0, -1.0]],
            [[-2.0, -2.0], [-2.0, 2.0], [2.0, 2.0], [2.0, -2.0], [-2.0, -2.0]],
        ],
        [
            [[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0], [-1.0, -1.0]],
            [[-2.0, -2.0], [-2.0, 2.0], [2.0, 2.0], [2.0, -2.0], [-2.0, -2.0]],
        ],
    ]
    result = mutation(
        "{ geofield: createGeoField(data: { multiPolygon: "
        + str(multi_polygon)
        + " }) { id } }"
    )
    assert not result.errors
    assert (
        deep_tuple_to_list(
            GeosFieldsModel.objects.get(
                id=result.data["geofield"]["id"]
            ).multi_polygon.tuple
        )
        == multi_polygon
    )
