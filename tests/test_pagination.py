from typing import List

import pytest
import strawberry

import strawberry_django
from strawberry_django import auto
from strawberry_django.pagination import PaginationConfig
from tests import models, utils


@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto


@strawberry_django.type(models.Fruit, pagination=True)
class BerryFruit:
    name: auto

    def get_queryset(self, queryset, info, **kwargs):
        return queryset.filter(name__contains="berry")


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field()
    fruits_paginated_by_default: List[Fruit] = strawberry_django.field(
        pagination_config=PaginationConfig(default_offset=1, default_limit=1),
    )
    fruits_at_most_one: List[Fruit] = strawberry_django.field(
        pagination_config=PaginationConfig(max_limit=1)
    )
    berries: List[BerryFruit] = strawberry_django.field()


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_pagination(query, fruits):
    result = query("{ fruits(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"name": "raspberry"},
    ]


def test_pagination_of_filtered_query(query, fruits):
    result = query("{ berries(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["berries"] == [
        {"name": "raspberry"},
    ]


def test_pagination_default_offset_and_limit(query, fruits):
    result = query("{ fruitsPaginatedByDefault { name } }")
    assert not result.errors
    assert result.data["fruitsPaginatedByDefault"] == [
        {"name": "raspberry"},
    ]


def test_pagination_max_limit(query, fruits):
    result = query("{ fruitsAtMostOne { name } }")
    assert not result.errors
    assert result.data["fruitsAtMostOne"] == [
        {"name": "strawberry"},
    ]


def test_pagination_max_limit_with_offset(query, fruits):
    result = query("{ fruitsAtMostOne(pagination: { offset: 1 }) { name } }")
    assert not result.errors
    assert result.data["fruitsAtMostOne"] == [
        {"name": "raspberry"},
    ]


def test_pagination_max_limit_with_too_big_limit(query, fruits):
    result = query("{ fruitsAtMostOne(pagination: { limit: 3 }) { name } }")
    assert not result.errors
    assert len(result.data["fruitsAtMostOne"]) == 1
