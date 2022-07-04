import pytest

from tests import models


def test_create(mutation):
    result = mutation('{ fruit: createFruit(data: { name: "strawberry" }) { id name } }')
    assert not result.errors
    assert result.data["fruit"] == {"id": "1", "name": "strawberry"}
    assert list(models.Fruit.objects.values("id", "name")) == [
        {"id": 1, "name": "strawberry"},
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_create_async(mutation):
    result = await mutation('{ fruit: createFruit(data: { name: "strawberry" }) { name } }')
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
