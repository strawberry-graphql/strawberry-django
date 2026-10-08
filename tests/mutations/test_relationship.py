"""Test the functionality of CUD relationships.

Foreign key relationships in a GraphQL API context.
It includes tests for one-to-many, many-to-one, and many-to-many relationships.
"""

import pytest
from django.db.models.signals import m2m_changed
from strawberry import UNSET

from strawberry_django.mutations import resolvers
from strawberry_django.mutations.types import ParsedObject, ParsedObjectList
from tests import models


@pytest.fixture
def color(db):
    return models.Color.objects.create(name="red")


@pytest.fixture
def fruit_type(db):
    return models.FruitType.objects.create(name="Berries")


def test_create_one_to_many(mutation, color, mocker):
    result = mutation(
        '{ fruit: createFruit(data: { name: "strawberry",'
        " color: { set: 1 } }) { color { name } } }",
    )
    assert not result.errors
    assert result.data["fruit"] == {"color": {"name": color.name}}

    fruit = resolvers.create(
        mocker.Mock(),
        models.Fruit,
        {
            "name": "banana",
            "color": ParsedObject(pk=UNSET, data={"name": "yellow"}),
        },
    )
    assert fruit.color is not None
    assert fruit.color.name == "yellow"
    assert models.Fruit.objects.get(pk=fruit.pk).color == models.Color.objects.get(
        name="yellow"
    )


def test_update_one_to_many(mutation, fruit, color):
    result = mutation(
        "{ fruits: updateFruits(data: { color: { set: 1 } }, filters: {}) { color { name } } }",
    )
    assert not result.errors
    assert result.data["fruits"] == [{"color": {"name": color.name}}]

    result = mutation(
        "{ fruits: updateFruits(data: { color: { set: null } }, filters: {}) { color { name } } }",
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


@pytest.mark.parametrize("action", ["set", "add"])
def test_create_many_to_many(mutation, fruit, mocker, action):
    result = mutation(
        '{ types: createFruitType(data: { name: "Berries",'
        " fruits: { set: [1] } }) { fruits { name } } }",
    )
    assert not result.errors
    assert result.data["types"] == {"fruits": [{"name": fruit.name}]}

    def rename_after_add(sender, instance, action, **kwargs):
        if action == "post_add":
            models.FruitType.objects.filter(pk=instance.pk).update(name="Fresh berries")

    # A signal can change the row during relation updates; create must refresh it.
    through = models.Fruit.types.through
    nested_fruits = ParsedObjectList()
    setattr(nested_fruits, action, [ParsedObject(pk=UNSET, data={"name": "raspberry"})])
    m2m_changed.connect(rename_after_add, sender=through)
    try:
        fruit_type = resolvers.create(
            mocker.Mock(),
            models.FruitType,
            {
                "name": "Berries",
                "fruits": nested_fruits,
            },
        )
    finally:
        m2m_changed.disconnect(rename_after_add, sender=through)

    assert fruit_type.name == "Fresh berries"
    assert list(
        models.Fruit.objects.filter(types=fruit_type).values_list("name", flat=True)
    ) == ["raspberry"]
    assert models.Fruit.objects.get(name="raspberry").types.get() == fruit_type


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
