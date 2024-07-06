"""Test the functionality of CUD relationships.

Foreign key relationships in a GraphQL API context.
It includes tests for one-to-many, many-to-one, and many-to-many relationships.
"""

import pytest

from tests import models


@pytest.fixture
def color(db):
    return models.Color.objects.create(name="red")


@pytest.fixture
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


def test_patch_one_to_many(mutation, fruit, color, django_assert_max_num_queries):
    # Issue 487: At maximum, 11 queries are expected to be executed:
    # 6x SAVEPOINT, 4x SELECT, 1x UPDATE
    with django_assert_max_num_queries(12):
        result = mutation(
            '{ fruits: updateFruits(filters: { id: { exact: "1"} }, '
            "data: { color: { set: 1 } }) { color { name } } }",
        )
    assert not result.errors
    assert result.data["fruits"] == [{"color": {"name": color.name}}]


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
