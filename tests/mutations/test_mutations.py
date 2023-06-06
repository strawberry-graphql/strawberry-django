import pytest
from django.conf import settings

from tests import models
from tests.utils import deep_tuple_to_list


def test_create(mutation):
    result = mutation(
        '{ fruit: createFruit(data: { name: "strawberry" }) { id name } }',
    )
    assert not result.errors
    assert result.data["fruit"] == {"id": "1", "name": "strawberry"}
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "strawberry"},
    ]


@pytest.mark.asyncio()
@pytest.mark.django_db(transaction=True)
async def test_create_async(mutation):
    result = await mutation(
        '{ fruit: createFruit(data: { name: "strawberry" }) { name } }',
    )
    assert not result.errors
    assert result.data["fruit"] == {"name": "strawberry"}


def test_create_many(mutation):
    result = mutation(
        (
            '{ fruits: createFruits(data: [{ name: "strawberry" },'
            ' { name: "raspberry" }]) { id name } }'
        ),
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
        (
            '{ fruits: updateFruits(data: { name: "orange" },'
            " filters: { id: { inList: [1, 2] } } ) { id name } }"
        ),
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
        (
            '{ fruits: deleteFruits(filters: { name: { contains: "berry" } }) { id'
            " name } }"
        ),
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
    point = (0.0, 1.0)
    result = mutation(
        f"{{ geofield: createGeoField(data: {{ point: {list(point)} }} ) {{ id }} }}",
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).point.tuple
        == point
    )

    # Test for lineString
    line_string = ((0.0, 0.0), (1.0, 1.0))
    result = mutation(
        f"""
        {{ geofield: createGeoField(data: {{ lineString:
            {deep_tuple_to_list(line_string)}
         }}) {{ id }} }}
        """,
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).line_string.tuple
        == line_string
    )

    # Test for polygon
    polygon = (
        ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
        ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
    )
    result = mutation(
        f"""
        {{ geofield: createGeoField(data: {{
            polygon: {deep_tuple_to_list(polygon)}
        }}) {{ id }} }}
        """,
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).polygon.tuple
        == polygon
    )

    # Test for multi_point
    multi_point = ((0.0, 0.0), (-1.0, -1.0), (1.0, 1.0))
    result = mutation(
        f"""
        {{ geofield: createGeoField(data: {{ multiPoint:
            {deep_tuple_to_list(multi_point)}
        }}) {{ id }} }}
        """,
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(id=result.data["geofield"]["id"]).multi_point.tuple
        == multi_point
    )

    # Test for multiLineString
    multi_line_string = (
        ((0.0, 0.0), (1.0, 1.0)),
        ((1.0, 1.0), (-1.0, -1.0)),
        ((2.0, 2.0), (-2.0, -2.0)),
    )
    result = mutation(
        f"""
        {{ geofield: createGeoField(data: {{ multiLineString:
            {deep_tuple_to_list(multi_line_string)}
        }}) {{ id }} }}
        """,
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(
            id=result.data["geofield"]["id"],
        ).multi_line_string.tuple
        == multi_line_string
    )

    # Test for multiPolygon
    multi_polygon = (
        (
            ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
            ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
        ),
        (
            ((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)),
            ((-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)),
        ),
    )
    result = mutation(
        f"""
        {{ geofield: createGeoField(data: {{ multiPolygon:
            {deep_tuple_to_list(multi_polygon)}
        }}) {{ id }} }}
        """,
    )
    assert not result.errors
    assert (
        GeosFieldsModel.objects.get(
            id=result.data["geofield"]["id"],
        ).multi_polygon.tuple
        == multi_polygon
    )


@pytest.mark.skipif(
    not settings.GEOS_IMPORTED,
    reason="Test requires GEOS to be imported and properly configured",
)
@pytest.mark.django_db(transaction=True)
def test_update_geo(mutation):
    from tests.models import GeosFieldsModel

    geofield_obj = GeosFieldsModel.objects.create()

    assert geofield_obj.point is None
    assert geofield_obj.line_string is None
    assert geofield_obj.polygon is None
    assert geofield_obj.multi_point is None
    assert geofield_obj.multi_line_string is None
    assert geofield_obj.multi_polygon is None

    obj_id = str(geofield_obj.id)

    # Test for point
    point = [0.0, 1.0]
    result = mutation(
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            point: {point}
            }}) {{
                id
            }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.point.tuple) == point

    # Test for lineString
    line_string = [[0.0, 0.0], [1.0, 1.0]]
    result = mutation(
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            lineString: {line_string}
            }}) {{
                id
            }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.line_string.tuple) == line_string

    # Test for polygon
    polygon = [
        [[-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0], [-1.0, -1.0]],
        [[-2.0, -2.0], [-2.0, 2.0], [2.0, 2.0], [2.0, -2.0], [-2.0, -2.0]],
    ]
    result = mutation(
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            polygon: {polygon}
            }}) {{
                id
        }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.polygon.tuple) == polygon

    # Test for multi_point
    multi_point = [[0.0, 0.0], [-1.0, -1.0], [1.0, 1.0]]
    result = mutation(
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            multiPoint: {multi_point}
            }}) {{
                id
            }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.multi_point.tuple) == multi_point

    # Test for multiLineString
    multi_line_string = [
        [[0.0, 0.0], [1.0, 1.0]],
        [[1.0, 1.0], [-1.0, -1.0]],
        [[2.0, 2.0], [-2.0, -2.0]],
    ]
    result = mutation(
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            multiLineString: {multi_line_string}
            }}) {{
                id
            }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.multi_line_string.tuple) == multi_line_string

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
        f"""
        {{ geofield: updateGeoFields(data: {{
            id: {obj_id} ,
            multiPolygon: {multi_polygon}
            }}) {{
                id
            }} }}
        """,
    )
    assert not result.errors
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.multi_polygon.tuple) == multi_polygon

    # Test everything not overwritten
    geofield_obj.refresh_from_db()
    assert deep_tuple_to_list(geofield_obj.point.tuple) == point
    assert deep_tuple_to_list(geofield_obj.line_string.tuple) == line_string
    assert deep_tuple_to_list(geofield_obj.polygon.tuple) == polygon
    assert deep_tuple_to_list(geofield_obj.multi_point.tuple) == multi_point
    assert deep_tuple_to_list(geofield_obj.multi_line_string.tuple) == multi_line_string
    assert deep_tuple_to_list(geofield_obj.multi_polygon.tuple) == multi_polygon
