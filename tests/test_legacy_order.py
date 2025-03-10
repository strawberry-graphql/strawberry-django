# ruff: noqa: TRY002, B904, BLE001, F811, PT012
import warnings
from typing import Any, Optional, cast
from unittest import mock

import pytest
import strawberry
from django.db.models import Case, Count, Value, When
from pytest_mock import MockFixture
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.types import get_object_definition
from strawberry.types.base import (
    StrawberryOptional,
    WithStrawberryObjectDefinition,
    get_object_definition,
)
from strawberry.types.field import StrawberryField

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


@strawberry_django.ordering.ordering(models.Fruit)
class FruitOrdering:
    name: auto


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
    fruits: list[Fruit] = strawberry_django.field(order=FruitOrder)
    fruits_with_ordering: list[Fruit] = strawberry_django.field(
        order=FruitOrder, ordering=FruitOrdering
    )


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_legacy_order_argument_is_deprecated():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)
        strawberry_django.field(order=FruitOrder)
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert (
            str(w[-1].message)
            == "strawberry_django.order is deprecated in favor of strawberry_django.ordering."
        )


def test_legacy_order_type_is_deprecated():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)

        @strawberry_django.ordering.order(models.Fruit)
        class TestOrder:
            name: auto

        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert (
            str(w[-1].message)
            == "strawberry_django.order is deprecated in favor of strawberry_django.ordering."
        )


def test_legacy_order_works_when_ordering_is_present(query, fruits):
    result = query("{ fruitsWithOrdering(order: { name: ASC }) { id name } }")
    assert not result.errors
    assert result.data["fruitsWithOrdering"] == [
        {"id": "3", "name": "banana"},
        {"id": "2", "name": "raspberry"},
        {"id": "1", "name": "strawberry"},
    ]


def test_ordering_works_when_legacy_order_is_present(query, fruits):
    result = query("{ fruitsWithOrdering(ordering: [{ name: ASC }]) { id name } }")
    assert not result.errors
    assert result.data["fruitsWithOrdering"] == [
        {"id": "3", "name": "banana"},
        {"id": "2", "name": "raspberry"},
        {"id": "1", "name": "strawberry"},
    ]


def test_error_when_ordering_and_order_given(query, fruits):
    result = query(
        "{ fruitsWithOrdering(ordering: [{ name: ASC }], order: { name: ASC }) { id name } }"
    )
    assert result.errors is not None and len(result.errors) == 1
    assert result.errors[0].message == "Only one of ordering, order must be given."


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
        raise pytest.fail(f"DID RAISE {exc}")


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
        raise pytest.fail(f"DID RAISE {exc}")


def test_order_field_method():
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        @strawberry_django.order_field
        def custom_order(self, root, info, prefix, value: auto, sequence, queryset):
            assert self == order, "Unexpected self passed"
            assert root == order, "Unexpected root passed"
            assert info == fake_info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert value == Ordering.ASC, "Unexpected value passed"
            assert sequence == sequence_inner, "Unexpected sequence passed"
            assert queryset == qs, "Unexpected queryset passed"
            raise Exception("WAS CALLED")

    order = cast("WithStrawberryObjectDefinition", Order(custom_order=Ordering.ASC))  # type: ignore
    schema = strawberry.Schema(query=Query)
    fake_info: Any = type("FakeInfo", (), {"schema": schema})
    qs: Any = object()
    sequence_inner: Any = object()
    sequence = {"customOrder": OrderSequence(0, children=sequence_inner)}

    with pytest.raises(Exception, match="WAS CALLED"):
        process_order(order, fake_info, qs, prefix="ROOT", sequence=sequence)


def test_order_method_not_called_when_not_decorated(mocker: MockFixture):
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        def order(self, root, info, prefix, value: auto, sequence, queryset):
            pytest.fail("Should not have been called")

    mock_order_method = mocker.spy(Order, "order")

    process_order(
        cast("WithStrawberryObjectDefinition", Order()), mock.Mock(), mock.Mock()
    )

    mock_order_method.assert_not_called()


def test_order_field_not_called(mocker: MockFixture):
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        order: Ordering = Ordering.ASC

    # Calling this and no error being raised is the test, as the wrong behavior would
    # be for the field to be called like a method
    process_order(
        cast("WithStrawberryObjectDefinition", Order()), mock.Mock(), mock.Mock()
    )


def test_order_object_method():
    @strawberry_django.ordering.order(models.Fruit)
    class Order:
        @strawberry_django.order_field
        def order(self, root, info, prefix, sequence, queryset):
            assert self == order_, "Unexpected self passed"
            assert root == order_, "Unexpected root passed"
            assert info == fake_info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert sequence == sequence_, "Unexpected sequence passed"
            assert queryset == qs, "Unexpected queryset passed"
            return queryset, ["name"]

    order_ = cast("WithStrawberryObjectDefinition", Order())
    schema = strawberry.Schema(query=Query)
    fake_info: Any = type("FakeInfo", (), {"schema": schema})
    qs: Any = object()
    sequence_: Any = {"customOrder": OrderSequence(0)}

    order = process_order(order_, fake_info, qs, prefix="ROOT", sequence=sequence_)[1]
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
