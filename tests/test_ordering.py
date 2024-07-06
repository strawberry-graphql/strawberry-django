# ruff: noqa: TRY002, B904, BLE001, F811, PT012
from typing import Any, List, Optional, cast

import pytest
import strawberry
from django.db.models import Case, Count, Value, When
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.field import StrawberryField
from strawberry.type import (
    StrawberryOptional,
    WithStrawberryObjectDefinition,
    get_object_definition,
)

import strawberry_django
from strawberry_django.exceptions import (
    ForbiddenFieldArgumentError,
    MissingFieldArgumentError,
)
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.fields.filter_order import (
    FilterOrderField,
    FilterOrderFieldResolver,
)
from strawberry_django.ordering import Ordering, OrderSequence, process_order
from tests import models, utils
from tests.types import Fruit


@strawberry_django.ordering.order(models.Color)
class ColorOrder:
    pk: auto

    @strawberry_django.order_field
    def name(self, prefix, value: auto):
        return [value.resolve(f"{prefix}name")]


@strawberry_django.ordering.order(models.Fruit)
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


@strawberry_django.type(models.Fruit, order=FruitOrder)
class FruitWithOrder:
    id: auto
    name: auto


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field(order=FruitOrder)


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_field_order_definition():
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


def test_order_sequence():
    f1 = StrawberryField(graphql_name="sOmEnAmE", python_name="some_name")
    f2 = StrawberryField(python_name="some_name")

    assert OrderSequence.get_graphql_name(None, f1) == "sOmEnAmE"
    assert OrderSequence.get_graphql_name(None, f2) == "someName"

    assert OrderSequence.sorted(None, None, fields=[f1, f2]) == [f1, f2]

    sequence = {"someName": OrderSequence(0, None), "sOmEnAmE": OrderSequence(1, None)}
    assert OrderSequence.sorted(None, sequence, fields=[f1, f2]) == [f1, f2]


def test_order_type():
    @strawberry_django.ordering.order(models.Fruit)
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


def test_order_field_missing_prefix():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"prefix\".*\"field_method\".*"
    ):

        @strawberry_django.order_field
        def field_method():
            pass


def test_order_field_missing_value():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"value\".*\"field_method\".*"
    ):

        @strawberry_django.order_field
        def field_method(prefix):
            pass


def test_order_field_missing_value_annotation():
    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r"Missing annotation.*\"value\".*\"field_method\".*",
    ):

        @strawberry_django.order_field
        def field_method(prefix, value):
            pass


def test_order_field():
    try:

        @strawberry_django.order_field
        def field_method(self, root, info, prefix, value: auto, sequence, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")  # type: ignore


def test_order_field_forbidden_param_annotation():
    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.order_field
        def field_method(prefix, value: auto, sequence, queryset, forbidden_param):
            pass


def test_order_field_forbidden_param():
    with pytest.raises(
        ForbiddenFieldArgumentError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.order_field
        def field_method(prefix, value: auto, sequence, queryset, forbidden_param: str):
            pass


def test_order_field_missing_queryset():
    with pytest.raises(MissingFieldArgumentError, match=r".*\"queryset\".*\"order\".*"):

        @strawberry_django.order_field
        def order(prefix):
            pass


def test_order_field_value_forbidden_on_object():
    with pytest.raises(ForbiddenFieldArgumentError, match=r".*\"value\".*\"order\".*"):

        @strawberry_django.order_field
        def field_method(prefix, queryset, value: auto):
            pass

        @strawberry_django.order_field
        def order(prefix, queryset, value: auto):
            pass


def test_order_field_on_object():
    try:

        @strawberry_django.order_field
        def order(self, root, info, prefix, sequence, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")  # type: ignore


def test_order_field_method():
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        @strawberry_django.order_field
        def custom_order(self, root, info, prefix, value: auto, sequence, queryset):
            assert self == _order, "Unexpected self passed"
            assert root == _order, "Unexpected root passed"
            assert info == _info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert value == Ordering.ASC, "Unexpected value passed"
            assert sequence == _sequence_inner, "Unexpected sequence passed"
            assert queryset == _queryset, "Unexpected queryset passed"
            raise Exception("WAS CALLED")

    _order = cast(WithStrawberryObjectDefinition, Order(custom_order=Ordering.ASC))  # type: ignore
    schema = strawberry.Schema(query=Query)
    _info: Any = type("FakeInfo", (), {"schema": schema})
    _queryset: Any = object()
    _sequence_inner: Any = object()
    _sequence = {"customOrder": OrderSequence(0, children=_sequence_inner)}

    with pytest.raises(Exception, match="WAS CALLED"):
        process_order(_order, _info, _queryset, prefix="ROOT", sequence=_sequence)


def test_order_object_method():
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        @strawberry_django.order_field
        def order(self, root, info, prefix, sequence, queryset):
            assert self == _order, "Unexpected self passed"
            assert root == _order, "Unexpected root passed"
            assert info == _info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert sequence == _sequence, "Unexpected sequence passed"
            assert queryset == _queryset, "Unexpected queryset passed"
            return queryset, ["name"]

    _order = cast(WithStrawberryObjectDefinition, Order())
    schema = strawberry.Schema(query=Query)
    _info: Any = type("FakeInfo", (), {"schema": schema})
    _queryset: Any = object()
    _sequence: Any = {"customOrder": OrderSequence(0)}

    order = process_order(_order, _info, _queryset, prefix="ROOT", sequence=_sequence)[
        1
    ]
    assert "name" in order, "order was not called"


def test_order_nulls(query, db, fruits):
    t1 = models.FruitType.objects.create(name="Type1")
    t2 = models.FruitType.objects.create(name="Type2")

    f1, f2, f3 = models.Fruit.objects.all()

    f2.types.add(t1)
    f3.types.add(t1, t2)

    result = query("{ fruits(order: { typesNumber: ASC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f2.id)},
        {"id": str(f3.id)},
    ]

    result = query("{ fruits(order: { typesNumber: DESC }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f3.id)},
        {"id": str(f2.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(order: { typesNumber: ASC_NULLS_FIRST }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f2.id)},
        {"id": str(f3.id)},
    ]

    result = query("{ fruits(order: { typesNumber: ASC_NULLS_LAST }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f2.id)},
        {"id": str(f3.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(order: { typesNumber: DESC_NULLS_LAST }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f3.id)},
        {"id": str(f2.id)},
        {"id": str(f1.id)},
    ]

    result = query("{ fruits(order: { typesNumber: DESC_NULLS_FIRST }) { id } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f3.id)},
        {"id": str(f2.id)},
    ]
