import pytest

from tests import models


@pytest.fixture()
def fruit(db):
    return models.Fruit.objects.create(name="Strawberry")


@pytest.fixture()
def color(db):
    return models.Color.objects.create(name="red")


@pytest.fixture()
def fruit_type(db):
    return models.FruitType.objects.create(name="Berries")


def test_create_one_to_many(mutation, color):
    result = mutation(
        '{ fruit: createFruit(data: { name: "strawberry",'
        " color: { set: 1 } }) { color { name } } }",
    )
    assert not result.errors
    assert result.data["fruit"] == {"color": {"name": color.name}}


def test_update_one_to_many(mutation, fruit, color):
    result = mutation(
        "{ fruits: updateFruits(data: { color: { set: 1 } }) { color { name } } }",
    )
    assert not result.errors
    assert result.data["fruits"] == [{"color": {"name": color.name}}]

    result = mutation(
        "{ fruits: updateFruits(data: { color: { set: null } }) { color { name } } }",
    )
    assert not result.errors
    assert result.data["fruits"] == [{"color": None}]


def test_update_many_to_one(mutation, fruit, color):
    result = mutation(
        "{ colors: updateColors(data: { fruits: { add: [1] } }) { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["colors"] == [{"fruits": [{"name": fruit.name}]}]

    result = mutation(
        "{ colors: updateColors(data: { fruits: { remove: [1] } }) { fruits { name"
        " } } }",
    )
    assert not result.errors
    assert result.data["colors"] == [{"fruits": []}]

    result = mutation(
        "{ colors: updateColors(data: { fruits: { set: [1] } }) { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["colors"] == [{"fruits": [{"name": fruit.name}]}]

    result = mutation(
        "{ colors: updateColors(data: { fruits: { set: [] } }) { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["colors"] == [{"fruits": []}]


def test_create_many_to_many(mutation, fruit):
    result = mutation(
        '{ types: createFruitType(data: { name: "Berries",'
        " fruits: { set: [1] } }) { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["types"] == {"fruits": [{"name": fruit.name}]}


def test_update_many_to_many(mutation, fruit, fruit_type):
    result = mutation(
        "{ types: updateFruitTypes(data: { fruits: { add: [1] } }) { fruits { name"
        " } } }",
    )
    assert not result.errors
    assert result.data["types"] == [{"fruits": [{"name": fruit.name}]}]

    result = mutation(
        "{ types: updateFruitTypes(data: { fruits: { remove: [1] } })"
        " { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["types"] == [{"fruits": []}]

    result = mutation(
        "{ types: updateFruitTypes(data: { fruits: { set: [1] } }) { fruits { name"
        " } } }",
    )
    assert not result.errors
    assert result.data["types"] == [{"fruits": [{"name": fruit.name}]}]

    result = mutation(
        "{ types: updateFruitTypes(data: { fruits: { set: [] } }) { fruits { name"
        " } } }",
    )
    assert not result.errors
    assert result.data["types"] == [{"fruits": []}]
