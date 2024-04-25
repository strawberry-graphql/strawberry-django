"""Tests for "batch mutations", mutations with a filter function that return a list."""


def test_delete_with_filter(mutation, fruits):
    result = mutation(
        """
        {
          fruits: deleteFruits(
            filters: {id: {exact: 1}}
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors


def test_delete_with_filter_empty_list(mutation, fruits):
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


def test_update_with_filter(mutation, fruits):
    result = mutation(
        """
        {
          fruits: updateFruits(
            data: { name: "orange" }
            filters: {id: {exact: 1}}
          ) {
            id
            name
          }
        }
        """
    )
    assert not result.errors


def test_update_with_filter_empty_list(mutation, fruits):
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
