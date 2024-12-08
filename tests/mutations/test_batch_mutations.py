"""Tests for batched mutations.

Batched mutations are mutations that mutate multiple objects at once.
Mutations with a filter function or accept a list of objects that return a list.
"""


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
