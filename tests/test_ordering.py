# ruff: noqa: TRY002, B904, BLE001, F811, PT012
import textwrap
from typing import Optional

import pytest
import strawberry
from django.db.models import Case, Count, Value, When
from django.db.models.functions import Reverse
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.base import (
    StrawberryOptional,
    get_object_definition,
)
from strawberry.types.field import StrawberryField

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.fields.filter_order import (
    FilterOrderField,
    FilterOrderFieldResolver,
)
from strawberry_django.ordering import Ordering
from tests import models, utils
from tests.types import Fruit


@strawberry_django.order_type(models.Color)
class ColorOrder:
    pk: auto

    @strawberry_django.order_field
    def name(self, prefix, value: auto):
        return [value.resolve(f"{prefix}name")]


@strawberry_django.order_type(models.Fruit)
class FruitOrder:
    color_id: auto
    name: auto
    sweetness: auto
    color: Optional[ColorOrder]

    @strawberry_django.order_field
    def types_number(self, queryset, prefix, value: auto):
        return queryset.annotate(
            count=Count(f"{prefix}types__id"),
            count_nulls=Case(
                When(count=0, then=Value(None)),
                default="count",
            ),
        ), [value.resolve("count_nulls")]


@strawberry_django.order_type(models.Fruit)
class CustomFruitOrder:
    reverse_name: auto

    @strawberry_django.order_field
    def order(self, info, queryset, prefix):
        queryset = queryset.annotate(reverse_name=Reverse(f"{prefix}name"))
        return strawberry_django.ordering.process_ordering_default(
            self, info, queryset, prefix
        )


@strawberry_django.type(models.Fruit, ordering=FruitOrder)
class FruitWithOrder:
    id: auto
    name: auto


@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field(ordering=FruitOrder)
    custom_order_fruits: list[Fruit] = strawberry_django.field(
        ordering=CustomFruitOrder
    )


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_correct_ordering_schema():
    @strawberry_django.type(models.Fruit, name="Fruit")
    class MiniFruit:
        id: auto
        name: auto

    @strawberry_django.order_type(models.Fruit, name="FruitOrder")
    class MiniFruitOrder:
        name: auto

    @strawberry.type(name="Query")
    class MiniQuery:
        fruits: list[MiniFruit] = strawberry_django.field(ordering=MiniFruitOrder)

    schema = strawberry.Schema(query=MiniQuery)
    expected = """\
    directive @oneOf on INPUT_OBJECT

    type Fruit {
      id: ID!
      name: String!
    }

    input FruitOrder @oneOf {
      name: Ordering
    }

    enum Ordering {
      ASC
      ASC_NULLS_FIRST
      ASC_NULLS_LAST
      DESC
      DESC_NULLS_FIRST
      DESC_NULLS_LAST
    }

    type Query {
      fruits(ordering: [FruitOrder!]! = []): [Fruit!]!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


def test_custom_order_method(query, fruits):
    result = query(
        "{ customOrderFruits(ordering: [{ reverseName: ASC }]) { id name } }"
    )
    assert not result.errors
    assert result.data["customOrderFruits"] == [
        {"id": "3", "name": "banana"},
        {"id": "2", "name": "raspberry"},
        {"id": "1", "name": "strawberry"},
    ]


def test_field_order_definition():
    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(FruitWithOrder))
    assert field.get_ordering() == FruitOrder
    field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(FruitWithOrder),
        ordering=None,
    )
    assert field.get_ordering() is None


def test_asc(query, fruits):
    result = query("{ fruits(ordering: [{ name: ASC }]) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana"},
        {"id": "2", "name": "raspberry"},
        {"id": "1", "name": "strawberry"},
    ]


def test_desc(query, fruits):
    result = query("{ fruits(ordering: [{ name: DESC }]) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
        {"id": "3", "name": "banana"},
    ]


def test_multi_order(query, db):
    for fruit in ("strawberry", "banana", "raspberry"):
        models.Fruit.objects.create(name=fruit, sweetness=7)

    result = query(
        "{ fruits(ordering: [{ sweetness: ASC }, { name: ASC }]) { id name sweetness } }"
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "2", "name": "banana", "sweetness": 7},
        {"id": "3", "name": "raspberry", "sweetness": 7},
        {"id": "1", "name": "strawberry", "sweetness": 7},
    ]


def test_relationship(query, fruits):
    def add_color(fruit, color_name):
        fruit.color = models.Color.objects.create(name=color_name)
        fruit.save()

    color_names = ["red", "dark red", "yellow"]
    for fruit, color_name in zip(fruits, color_names):
        add_color(fruit, color_name)
    result = query(
        "{ fruits(ordering: [{ color: { name: DESC } }]) { id name color { name } } }",
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana", "color": {"name": "yellow"}},
        {"id": "1", "name": "strawberry", "color": {"name": "red"}},
        {"id": "2", "name": "raspberry", "color": {"name": "dark red"}},
    ]


def test_multi_order_respected(query, db):
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

    result = query("{ fruits(ordering: [{ name: ASC }, { sweetness: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f2, f1]]

    result = query("{ fruits(ordering: [{ sweetness: DESC }, { name: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f1, f3]]

    result = query(
        "{ fruits(ordering: [{ color: {name: ASC} }, { name: ASC }]) { id } }"
    )
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f1, f2]]

    result = query("{ fruits(ordering: [{ color: {pk: ASC} }, { name: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f3, f1]]

    result = query("{ fruits(ordering: [{ colorId: ASC }, { name: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f2, f3, f1]]

    result = query("{ fruits(ordering: [{ name: ASC }, { colorId: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [{"id": str(f.pk)} for f in [f3, f2, f1]]


def test_order_type():
    @strawberry_django.ordering.order_type(models.Fruit)
    class FruitOrder:
        color_id: auto
        name: auto
        sweetness: auto

        @strawberry_django.order_field
        def custom_order(self, value: auto, prefix: str):
            pass

    annotated_type = StrawberryOptional(Ordering._enum_definition)  # type: ignore

    assert [
        (
            f.name,
            f.__class__,
            f.type,
            f.base_resolver.__class__ if f.base_resolver else None,
        )
        for f in get_object_definition(FruitOrder, strict=True).fields
    ] == [
        ("color_id", StrawberryField, annotated_type, None),
        ("name", StrawberryField, annotated_type, None),
        ("sweetness", StrawberryField, annotated_type, None),
        (
            "custom_order",
            FilterOrderField,
            annotated_type,
            FilterOrderFieldResolver,
        ),
    ]


def test_order_nulls(query, db, fruits):
    t1 = models.FruitType.objects.create(name="Type1")
    t2 = models.FruitType.objects.create(name="Type2")

    f1, f2, f3 = models.Fruit.objects.all()

    f2.types.add(t1)
    f3.types.add(t1, t2)

    result = query("{ fruits(ordering: [{ typesNumber: ASC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f2.id)},
        {"id": str(f3.id)},
    ]

    result = query("{ fruits(ordering: [{ typesNumber: DESC }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f3.id)},
        {"id": str(f2.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(ordering: [{ typesNumber: ASC_NULLS_FIRST }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f2.id)},
        {"id": str(f3.id)},
    ]

    result = query("{ fruits(ordering: [{ typesNumber: ASC_NULLS_LAST }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f2.id)},
        {"id": str(f3.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(ordering: [{ typesNumber: DESC_NULLS_LAST }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f3.id)},
        {"id": str(f2.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(ordering: [{ typesNumber: DESC_NULLS_FIRST }]) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f3.id)},
        {"id": str(f2.id)},
    ]
