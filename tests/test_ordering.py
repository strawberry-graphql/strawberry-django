from typing import List

import pytest
import strawberry
from strawberry import auto

import strawberry_django
from tests import models, utils
from tests.types import Fruit


@strawberry_django.ordering.order(models.Color)
class ColorOrder:
    name: auto


@strawberry_django.ordering.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field(order=FruitOrder)


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_asc(query, fruits):
    result = query("{ fruits(order: { name: ASC }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana"},
        {"id": "2", "name": "raspberry"},
        {"id": "1", "name": "strawberry"},
    ]


def test_desc(query, fruits):
    result = query("{ fruits(order: { name: DESC }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
        {"id": "3", "name": "banana"},
    ]


def test_relationship(query, fruits):
    def add_color(fruit, color_name):
        fruit.color = models.Color.objects.create(name=color_name)
        fruit.save()

    color_names = ["red", "dark red", "yellow"]
    for fruit, color_name in zip(fruits, color_names):
        add_color(fruit, color_name)
    result = query("{ fruits(order: { color: { name: DESC } }) { id name color { name } } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana", "color": {"name": "yellow"}},
        {"id": "1", "name": "strawberry", "color": {"name": "red"}},
        {"id": "2", "name": "raspberry", "color": {"name": "dark red"}},
    ]
