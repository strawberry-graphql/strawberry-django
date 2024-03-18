# ruff: noqa: TRY002, B904, BLE001, F811, PT012, A001, PLC2701
from enum import Enum
from typing import Any, List, Optional, cast

import pytest
import strawberry
from django.db.models import Case, Count, Q, QuerySet, Value, When
from strawberry import auto
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.relay import GlobalID
from strawberry.type import WithStrawberryObjectDefinition, get_object_definition

import strawberry_django
from strawberry_django.exceptions import (
    ForbiddenFieldArgumentError,
    MissingFieldArgumentError,
)
from strawberry_django.fields import filter_types
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.fields.filter_order import (
    FilterOrderField,
    FilterOrderFieldResolver,
)
from strawberry_django.filters import _resolve_value, process_filters
from tests import models, utils
from tests.types import Fruit, FruitType


@strawberry.enum
class Version(Enum):
    ONE = "first"
    TWO = "second"
    THREE = "third"


@strawberry_django.filter(models.Color, lookups=True)
class ColorFilter:
    id: auto
    name: auto

    @strawberry_django.filter_field
    def name_simple(self, prefix: str, value: str):
        return Q(**{f"{prefix}name": value})


@strawberry_django.filter(models.FruitType, lookups=True)
class FruitTypeFilter:
    name: auto
    fruits: Optional["FruitFilter"]


@strawberry_django.filter(models.Fruit, lookups=True)
class FruitFilter:
    color_id: auto
    name: auto
    sweetness: auto
    color: Optional[ColorFilter]
    types: Optional[FruitTypeFilter]

    @strawberry_django.filter_field
    def types_number(
        self,
        info,
        queryset: QuerySet,
        prefix,
        value: filter_types.ComparisonFilterLookup[int],
    ):
        return process_filters(
            cast(WithStrawberryObjectDefinition, value),
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
    def double(
        self,
        queryset: QuerySet,
        prefix,
        value: bool,
    ):
        return queryset.union(queryset, all=True), Q()

    @strawberry_django.filter_field
    def filter(self, info, queryset: QuerySet, prefix):
        return process_filters(
            cast(WithStrawberryObjectDefinition, self),
            queryset.filter(~Q(**{f"{prefix}name": "DARK_BERRY"})),
            info,
            prefix,
            skip_object_filter_method=True,
        )


@strawberry.type
class Query:
    types: List[FruitType] = strawberry_django.field(filters=FruitTypeFilter)
    fruits: List[Fruit] = strawberry_django.field(filters=FruitFilter)


@pytest.fixture()
def query():
    return utils.generate_query(Query)


@pytest.mark.parametrize(
    ("value", "resolved"),
    [
        (2, 2),
        ("something", "something"),
        (GlobalID("", "24"), "24"),
        (Version.ONE, Version.ONE.value),
        (
            [1, "str", GlobalID("", "24"), Version.THREE],
            [1, "str", "24", Version.THREE.value],
        ),
    ],
)
def test_resolve_value(value, resolved):
    assert _resolve_value(value) == resolved


def test_filter_field_missing_prefix():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"prefix\".*\"field_method\".*"
    ):

        @strawberry_django.filter_field
        def field_method():
            pass


def test_filter_field_missing_value():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"value\".*\"field_method\".*"
    ):

        @strawberry_django.filter_field
        def field_method(prefix):
            pass


def test_filter_field_missing_value_annotation():
    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r"Missing annotation.*\"value\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value):
            pass


def test_filter_field():
    try:

        @strawberry_django.filter_field
        def field_method(self, root, info, prefix, value: str, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")  # type: ignore


def test_filter_field_sequence():
    with pytest.raises(
        ForbiddenFieldArgumentError,
        match=r".*\"sequence\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, sequence, queryset):
            pass


def test_filter_field_forbidden_param_annotation():
    with pytest.raises(
        MissingArgumentsAnnotationsError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, queryset, forbidden_param):
            pass


def test_filter_field_forbidden_param():
    with pytest.raises(
        ForbiddenFieldArgumentError,
        match=r".*\"forbidden_param\".*\"field_method\".*",
    ):

        @strawberry_django.filter_field
        def field_method(prefix, value: auto, queryset, forbidden_param: str):
            pass


def test_filter_field_missing_queryset():
    with pytest.raises(
        MissingFieldArgumentError, match=r".*\"queryset\".*\"filter\".*"
    ):

        @strawberry_django.filter_field
        def filter(prefix):
            pass


def test_filter_field_value_forbidden_on_object():
    with pytest.raises(ForbiddenFieldArgumentError, match=r".*\"value\".*\"filter\".*"):

        @strawberry_django.filter_field
        def field_method(prefix, queryset, value: auto):
            pass

        @strawberry_django.filter_field
        def filter(prefix, queryset, value: auto):
            pass


def test_filter_field_on_object():
    try:

        @strawberry_django.filter_field
        def filter(self, root, info, prefix, queryset):
            pass
    except Exception as exc:
        raise pytest.fail(f"DID RAISE {exc}")  # type: ignore


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
            return Q(name=1)

    _filter: Any = Filter(custom_filter="SOMETHING")  # type: ignore
    _info: Any = object()
    _queryset: Any = object()

    q_object = process_filters(_filter, _queryset, _info, prefix="ROOT")[1]
    assert q_object, "Filter was not called"


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
            return queryset, Q(name=1)

    _filter: Any = Filter()
    _info: Any = object()
    _queryset: Any = object()

    q_object = process_filters(_filter, _queryset, _info, prefix="ROOT")[1]
    assert q_object, "Filter was not called"


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
            f.type.of_type.__name__,  # type: ignore
            f.base_resolver.__class__ if f.base_resolver else None,  # type: ignore
        )
        for f in get_object_definition(FruitOrder, strict=True).fields
        if f.name not in {"NOT", "AND", "OR", "DISTINCT"}
    ] == [
        ("id", StrawberryDjangoField, "BaseFilterLookup", None),
        ("name", StrawberryDjangoField, "FilterLookup", None),
        ("sweetness", StrawberryDjangoField, "ComparisonFilterLookup", None),
        (
            "custom_filter",
            FilterOrderField,
            "str",
            FilterOrderFieldResolver,
        ),
        (
            "custom_filter2",
            FilterOrderField,
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
            NOT: { color: { nameSimple: "sample" } }
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


def test_filter_distinct(query, db, fruits):
    t1 = models.FruitType.objects.create(name="type_1")
    t2 = models.FruitType.objects.create(name="type_2")

    f1 = models.Fruit.objects.all()[0]

    f1.types.add(t1, t2)

    result = query("""
    {
        fruits(
            filters: {types: { name: { iContains: "type" } } }
        ) { id name }
    }
    """)
    assert not result.errors
    assert len(result.data["fruits"]) == 2

    result = query("""
    {
        fruits(
            filters: {
                DISTINCT: true,
                types: { name: { iContains: "type" } }
            }
        ) { id name }
    }
    """)
    assert not result.errors
    assert len(result.data["fruits"]) == 1
