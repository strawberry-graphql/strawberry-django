# ruff: noqa: B904, BLE001, F811, PT012, A001
from enum import Enum
from typing import Annotated, Any, Optional, cast

import pytest
import strawberry
from django.db.models import Case, Count, Q, QuerySet, Value, When
from strawberry import auto
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.relay import GlobalID
from strawberry.types import ExecutionResult, get_object_definition
from strawberry.types.base import WithStrawberryObjectDefinition, get_object_definition
from typing_extensions import Self

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
    filter_field,
)
from strawberry_django.filters import process_filters, resolve_value
from tests import models, utils
from tests.types import Fruit, FruitType, Vegetable


@strawberry.enum
class Version(Enum):
    ONE = "first"
    TWO = "second"
    THREE = "third"


@strawberry_django.filter_type(models.Vegetable, lookups=True)
class VegetableFilter:
    id: auto
    name: auto
    AND: Optional[list[Self]] = strawberry.UNSET
    OR: Optional[list[Self]] = strawberry.UNSET
    NOT: Optional[list[Self]] = strawberry.UNSET


@strawberry_django.filter_type(models.Color, lookups=True)
class ColorFilter:
    id: auto
    name: auto

    @strawberry_django.filter_field
    def name_simple(self, prefix: str, value: str):
        return Q(**{f"{prefix}name": value})


@strawberry_django.filter_type(models.FruitType, lookups=True)
class FruitTypeFilter:
    name: auto
    fruits: Optional[
        Annotated["FruitFilter", strawberry.lazy("tests.filters.test_filters_v2")]
    ]


@strawberry_django.filter_type(models.Fruit, lookups=True)
class FruitFilter:
    color_id: auto
    name: auto
    sweetness: auto
    types: Optional[FruitTypeFilter]
    color: Optional[ColorFilter] = filter_field(filter_none=True)

    @strawberry_django.filter_field
    def types_number(
        self,
        info,
        queryset: QuerySet,
        prefix,
        value: filter_types.ComparisonFilterLookup[int],
    ):
        return process_filters(
            cast("WithStrawberryObjectDefinition", value),
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
            cast("WithStrawberryObjectDefinition", self),
            queryset.filter(~Q(**{f"{prefix}name": "DARK_BERRY"})),
            info,
            prefix,
            skip_object_filter_method=True,
        )


@strawberry.type
class Query:
    types: list[FruitType] = strawberry_django.field(filters=FruitTypeFilter)
    fruits: list[Fruit] = strawberry_django.field(filters=FruitFilter)
    vegetables: list[Vegetable] = strawberry_django.field(filters=VegetableFilter)


@pytest.fixture
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
    assert resolve_value(value) == resolved


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
        raise pytest.fail(f"DID RAISE {exc}")


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
        raise pytest.fail(f"DID RAISE {exc}")


def test_filter_field_method():
    @strawberry_django.filter_type(models.Fruit)
    class Filter:
        @strawberry_django.order_field
        def custom_filter(self, root, info, prefix, value: auto, queryset):
            assert self == filter_, "Unexpected self passed"
            assert root == filter_, "Unexpected root passed"
            assert info == fake_info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert value == "SOMETHING", "Unexpected value passed"
            assert queryset == qs, "Unexpected queryset passed"
            return Q(name=1)

    filter_: Any = Filter(custom_filter="SOMETHING")  # type: ignore
    fake_info: Any = object()
    qs: Any = object()

    q_object = process_filters(filter_, qs, fake_info, prefix="ROOT")[1]
    assert q_object, "Filter was not called"


def test_filter_object_method():
    @strawberry_django.filters.filter_type(models.Fruit)
    class Filter:
        @strawberry_django.filter_field
        def field_filter(self, value: str, prefix):
            raise AssertionError("Never called due to object filter override")

        @strawberry_django.filter_field
        def filter(self, root, info, prefix, queryset):
            assert self == filter_, "Unexpected self passed"
            assert root == filter_, "Unexpected root passed"
            assert info == fake_info, "Unexpected info passed"
            assert prefix == "ROOT", "Unexpected prefix passed"
            assert queryset == qs, "Unexpected queryset passed"
            return queryset, Q(name=1)

    filter_: Any = Filter()
    fake_info: Any = object()
    qs: Any = object()

    q_object = process_filters(filter_, qs, fake_info, prefix="ROOT")[1]
    assert q_object, "Filter was not called"


def test_filter_value_resolution():
    @strawberry_django.filters.filter_type(models.Fruit)
    class Filter:
        id: Optional[strawberry_django.ComparisonFilterLookup[GlobalID]]

    gid = GlobalID("FruitNode", "125")
    filter_: Any = Filter(
        id=strawberry_django.ComparisonFilterLookup(
            exact=gid, range=strawberry_django.RangeLookup(start=gid, end=gid)
        )
    )
    object_: Any = object()
    q = process_filters(filter_, object_, object_)[1]
    assert q == Q(id__exact="125", id__range=["125", "125"])


def test_filter_method_value_resolution():
    @strawberry_django.filters.filter_type(models.Fruit)
    class Filter:
        @strawberry_django.filter_field(resolve_value=True)
        def field_filter_resolved(self, value: GlobalID, prefix):
            assert isinstance(value, str)
            return Q()

        @strawberry_django.filter_field
        def field_filter_skip_resolved(self, value: GlobalID, prefix):
            assert isinstance(value, GlobalID)
            return Q()

    gid = GlobalID("FruitNode", "125")
    filter_: Any = Filter(field_filter_resolved=gid, field_filter_skip_resolved=gid)  # type: ignore
    object_: Any = object()
    process_filters(filter_, object_, object_)


def test_filter_type():
    @strawberry_django.filter_type(models.Fruit, lookups=True)
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


def test_filter_and_or_not(query, db):
    v1 = models.Vegetable.objects.create(
        name="v1", description="d1", world_production=100
    )
    v2 = models.Vegetable.objects.create(
        name="v2", description="d2", world_production=200
    )
    v3 = models.Vegetable.objects.create(
        name="v3", description="d3", world_production=300
    )

    # Test impossible AND
    result = query("""
    {
        vegetables(filters: { AND: [{ name: { exact: "v1" } }, { name: { exact: "v2" } }] }) { id }
    }
    """)
    assert not result.errors
    assert len(result.data["vegetables"]) == 0

    # Test AND with contains
    result = query("""
    {
        vegetables(filters: { AND: [{ name: { contains: "v" } }, { name: { contains: "2" } }] }) { id }
    }
    """)
    assert not result.errors
    assert len(result.data["vegetables"]) == 1
    assert result.data["vegetables"][0]["id"] == str(v2.pk)

    # Test OR
    result = query("""
    {
        vegetables(filters: { OR: [{ name: { exact: "v1" } }, { name: { exact: "v3" } }] }) { id }
    }
    """)
    assert not result.errors
    assert len(result.data["vegetables"]) == 2
    assert {
        result.data["vegetables"][0]["id"],
        result.data["vegetables"][1]["id"],
    } == {str(v1.pk), str(v3.pk)}

    # Test NOT
    result = query("""
    {
        vegetables(filters: { NOT: [{ name: { exact: "v1" } }, { name: { exact: "v2" } }] }) { id }
    }
    """)
    assert not result.errors
    assert len(result.data["vegetables"]) == 1
    assert result.data["vegetables"][0]["id"] == str(v3.pk)

    # Test interaction with simple filters. No matches due to AND logic relative to simple filters.
    result = query(
        """
    {
        vegetables(filters: { id: { exact: """
        + str(v1.pk)
        + """ }, AND: [{ name: { exact: "v2" } }] }) { id }
    }
    """
    )
    assert not result.errors
    assert len(result.data["vegetables"]) == 0

    # Test interaction with simple filters. Match on same record
    result = query(
        """
    {
        vegetables(filters: { id: { exact: """
        + str(v1.pk)
        + """ }, AND: [{ name: { exact: "v1" } }] }) { id }
    }
    """
    )
    assert not result.errors
    assert len(result.data["vegetables"]) == 1
    assert result.data["vegetables"][0]["id"] == str(v1.pk)


def test_filter_none(query, db):
    yellow = models.Color.objects.create(name="yellow")
    models.Fruit.objects.create(name="banana", color=yellow)

    f1 = models.Fruit.objects.create(name="unknown")
    f2 = models.Fruit.objects.create(name="unknown2")

    result = query("""
    {
        fruits(filters: {color: null}) { id }
    }
    """)

    assert not result.errors
    assert result.data["fruits"] == [
        {"id": str(f1.id)},
        {"id": str(f2.id)},
    ]


def test_empty_resolver_filter():
    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(self, filters: FruitFilter) -> list[Fruit]:
            queryset = models.Fruit.objects.none()
            info: Any = object()
            return cast(
                "list[Fruit]", strawberry_django.filters.apply(filters, queryset, info)
            )

    query = utils.generate_query(Query)
    result = query('{ fruits(filters: { name: { exact: "strawberry" } }) { name } }')
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["fruits"] == []


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_resolver_filter(fruits):
    @strawberry.type
    class Query:
        @strawberry.field
        async def fruits(self, filters: FruitFilter) -> list[Fruit]:
            queryset = models.Fruit.objects.all()
            info: Any = object()
            queryset = strawberry_django.filters.apply(filters, queryset, info)
            # cast fixes funny typing issue between list and List
            return cast("list[Fruit]", [fruit async for fruit in queryset])

    query = utils.generate_query(Query)
    result = await query(  # type: ignore
        '{ fruits(filters: { name: { exact: "strawberry" } }) { name } }'
    )
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["fruits"] == [
        {"name": "strawberry"},
    ]
