# ruff: noqa: TRY002, B904, BLE001, F811, PT012, A001
from typing import List, Optional

import pytest
import strawberry
from django.db.models import Case, Count, Q, QuerySet, Value, When
from strawberry import auto
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.type import get_object_definition

import strawberry_django
from strawberry_django.exceptions import (
    ForbiddenFieldArgumentError,
    MissingFieldArgumentError,
)
from strawberry_django.fields import filter_types
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.fields.filter_order import (
    FilterOrderFieldResolver,
    StrawberryDjangoFilterOrderField,
)
from strawberry_django.filters import process_filters
from tests import models, utils
from tests.types import Fruit


@strawberry_django.filter(models.Color, lookups=True)
class ColorFilter:
    id: auto
    name: auto


@strawberry_django.filter(models.Fruit, lookups=True)
class FruitFilter:
    color_id: auto
    name: auto
    sweetness: auto
    color: Optional[ColorFilter]

    @strawberry_django.filter_field
    def types_number(
        self,
        info,
        queryset: QuerySet,
        prefix,
        value: filter_types.ComparisonFilterLookup[int],
    ):
        return process_filters(
            value,
            queryset.annotate(
                count=Count(f"{prefix}types__id"),
                count_nulls=Case(
                    When(count=0, then=Value(None)),
                    default="count",
                ),
            ),
            info,
            "count_nulls__",
        )

    @strawberry_django.filter_field
    def filter(self, info, queryset: QuerySet, prefix):
        return process_filters(
            self,
            queryset.filter(~Q(**{f"{prefix}name": "DARK_BERRY"})),
            info,
            prefix,
            skip_object_filter_method=True,
        )


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field(filters=FruitFilter)


@pytest.fixture()
def query():
    return utils.generate_query(Query)


def test_filter_field_validation():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"prefix\".*\"field_method\".*"
    ):

        @strawberry_django.filter_field
        def field_method():
            pass

    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"value\".*\"field_method\".*"
    ):

        @strawberry_django.filter_field
        def field_method(prefix):
            pass

    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r"Missing annotation.*\"value\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value):
            pass

    try:

        @strawberry_django.filter_field
        def field_method(self, root, info, prefix, value: str, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")

    with pytest.raises(
        Exception,
        match=r".*\"sequence\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, sequence, queryset):
            pass

    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, queryset, forbidden_param):
            pass

    with pytest.raises(
        ForbiddenFieldArgumentError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, queryset, forbidden_param: str):
            pass

    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"queryset\".*\"filter\".*"
    ):

        @strawberry_django.filter_field
        def filter(prefix):
            pass

    with pytest.raises(ForbiddenFieldArgumentError, match=r".*\"value\".*\"filter\".*"):

        @strawberry_django.filter_field
        def field_method(prefix, queryset, value: auto):
            pass

        @strawberry_django.filter_field
        def filter(prefix, queryset, value: auto):
            pass

    try:

        @strawberry_django.filter_field
        def filter(self, root, info, prefix, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")


def test_filter_field_method():
    @strawberry_django.filter(models.Fruit)
    class Filter:
        @strawberry_django.order_field
        def custom_filter(self, root, info, prefix, value: auto, queryset):
            assert self == _filter, "Unexpected self passed"
            assert root == _filter, "Unexpected root passed"
            assert info == _info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert value == "SOMETHING", "Unexpected value passed"
            assert queryset == _queryset, "Unexpected queryset passed"
            raise Exception("WAS CALLED")

    _filter = Filter(custom_filter="SOMETHING")
    _info = object()
    _queryset = object()

    with pytest.raises(Exception, match="WAS CALLED"):
        process_filters(_filter, _queryset, _info, prefix="ROOT")


def test_filter_object_method():
    @strawberry_django.ordering.order(models.Fruit)
    class Filter:
        @strawberry_django.order_field
        def field_filter(self, value: str, prefix):
            raise AssertionError("Never called due to object filter override")

        @strawberry_django.order_field
        def filter(self, root, info, prefix, queryset):
            assert self == _filter, "Unexpected self passed"
            assert root == _filter, "Unexpected root passed"
            assert info == _info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert queryset == _queryset, "Unexpected queryset passed"
            raise Exception("WAS CALLED")

    _filter = Filter()
    _info = object()
    _queryset = object()

    with pytest.raises(Exception, match="WAS CALLED"):
        process_filters(_filter, _queryset, _info, prefix="ROOT")


def test_filter_type():
    @strawberry_django.filter(models.Fruit, lookups=True)
    class FruitOrder:
        id: auto
        name: auto
        sweetness: auto

        @strawberry_django.filter_field
        def custom_filter(self, value: str, prefix: str):
            pass

        @strawberry_django.filter_field
        def custom_filter2(
            self, value: filter_types.BaseFilterLookup[str], prefix: str
        ):
            pass

    assert [
        (
            f.name,
            f.__class__,
            f.type.of_type.__name__,
            f.base_resolver.__class__ if f.base_resolver else None,
        )
        for f in get_object_definition(FruitOrder, strict=True).fields
        if f.name not in {"NOT", "AND", "OR", "DISTINCT"}
    ] == [
        ("id", StrawberryDjangoField, "BaseFilterLookup", None),
        ("name", StrawberryDjangoField, "FilterLookup", None),
        ("sweetness", StrawberryDjangoField, "ComparisonFilterLookup", None),
        (
            "custom_filter",
            StrawberryDjangoFilterOrderField,
            "str",
            FilterOrderFieldResolver,
        ),
        (
            "custom_filter2",
            StrawberryDjangoFilterOrderField,
            "BaseFilterLookup",
            FilterOrderFieldResolver,
        ),
    ]


def test_filter_methods(query, db, fruits):
    t1 = models.FruitType.objects.create(name="Type1")
    t2 = models.FruitType.objects.create(name="Type2")

    f1, f2, f3 = models.Fruit.objects.all()
    _ = models.Fruit.objects.create(name="DARK_BERRY")

    f2.types.add(t1)
    f3.types.add(t1, t2)

    result = query("""
    {
        fruits(filters: {
            typesNumber: { gt: 1 }
            OR: {
                typesNumber: { isNull: true }
            }
        }) { id } }
    """)

    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f3.id)},
    ]
