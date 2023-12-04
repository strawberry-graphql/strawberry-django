from typing import List, Optional

import pytest
import strawberry
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation

import strawberry_django
from tests import models, utils
from tests.types import Fruit


@strawberry_django.ordering.order(models.Color)
class ColorOrder:
    pk: auto
    name: auto


@strawberry_django.ordering.order(models.Fruit)
class FruitOrder:
    color_id: auto
    name: auto
    sweetness: auto
    color: Optional[ColorOrder]


@strawberry_django.type(models.Fruit, order=FruitOrder)
class FruitWithOrder:
    id: auto
    name: auto


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field(order=FruitOrder)


@pytest.fixture()
def query():
    return utils.generate_query(Query)


def test_field_order_definition():
    from strawberry_django.fields.field import StrawberryDjangoField

    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(FruitWithOrder))
    assert field.get_order() == FruitOrder
    field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(FruitWithOrder),
        filters=None,
    )
    assert field.get_filters() is None


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
    result = query(
        "{ fruits(order: { color: { name: DESC } }) { id name color { name } } }",
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana", "color": {"name": "yellow"}},
        {"id": "1", "name": "strawberry", "color": {"name": "red"}},
        {"id": "2", "name": "raspberry", "color": {"name": "dark red"}},
    ]


def test_arguments_order_respected(query, db):
    yellow = models.Color.objects.create(name="yellow")
    red = models.Color.objects.create(name="red")

    f1 = models.Fruit.objects.create(
        name="strawberry",
        sweetness=1,
        color=red,
    )
    f2 = models.Fruit.objects.create(
        name="banana",
        sweetness=2,
        color=yellow,
    )
    f3 = models.Fruit.objects.create(
        name="apple",
        sweetness=0,
        color=red,
    )

    result = query("{ fruits(order: { name: ASC, sweetness: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f2, f1]]

    result = query("{ fruits(order: { sweetness: DESC, name: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f1, f3]]

    result = query("{ fruits(order: { color: {name: ASC}, name: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f1, f2]]

    result = query("{ fruits(order: { color: {pk: ASC}, name: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f3, f1]]

    result = query("{ fruits(order: { colorId: ASC, name: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f3, f1]]

    result = query("{ fruits(order: { name: ASC, colorId: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f2, f1]]
