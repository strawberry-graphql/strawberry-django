"""Tests for batched mutations.

Batched mutations are mutations that mutate multiple objects at once.
Mutations with a filter function or accept a list of objects that return a list.
"""

from typing import Any

from strawberry_django.mutations import resolvers
from tests import models


def test_batch_create(mutation, fruits):
    result = mutation(
        """
        mutation {
          fruits: createFruits(
            data: [{ name: "banana" }, { name: "cherry" }]
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "4", "name": "banana"},
        {"id": "5", "name": "cherry"},
    ]


def test_batch_create_with_pre_save_hook(db):
    prepared = []

    def pre_save_hook(instance):
        assert instance.pk is None
        prepared.append(instance)
        instance.name = instance.name.upper()

    info: Any = None
    instances = resolvers.create(
        info,
        models.Fruit,
        [
            {"name": "banana", "types": [{"name": "excluded"}]},
            {"name": "cherry", "types": [{"name": "excluded"}]},
        ],
        pre_save_hook=pre_save_hook,
        exclude_m2m=["types"],
    )

    assert len(prepared) == 2
    assert all(
        instance is seen for instance, seen in zip(instances, prepared, strict=True)
    )
    assert [instance.name for instance in instances] == ["BANANA", "CHERRY"]
    assert list(models.Fruit.objects.order_by("pk").values_list("name", flat=True)) == [
        "BANANA",
        "CHERRY",
    ]
    assert not models.FruitType.objects.exists()
    assert all(not instance.types.exists() for instance in instances)


def test_batch_delete_with_filter(mutation, fruits):
    result = mutation(
        """
        mutation($ids: [ID!]) {
          fruits: deleteFruits(
            filters: {id: {inList: $ids}}
          ) {
            id
            name
          }
        }
        """,
        {"ids": ["2"]},
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "2", "name": "raspberry"},
    ]


def test_batch_delete_with_filter_empty_list(mutation, fruits):
    result = mutation(
        """
        {
          fruits: deleteFruits(
            filters: {id: {inList: []}}
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors


def test_batch_update_with_filter(mutation, fruits):
    result = mutation(
        """
        {
          fruits: updateFruits(
            data: { name: "orange" }
            filters: {id: {inList: [1]}}
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "orange"},
    ]


def test_batch_update_with_filter_empty_list(mutation, fruits):
    result = mutation(
        """
        {
          fruits: updateFruits(
            data: { name: "orange" }
            filters: {id: {inList: []}}
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors


def test_batch_patch(mutation, fruits):
    result = mutation(
        """
        {
          fruits: patchFruits(
            data: [{ id: 2, name: "orange" }]
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "2", "name": "orange"},
    ]
