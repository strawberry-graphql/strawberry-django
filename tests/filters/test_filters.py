from enum import Enum
from typing import List

import pytest
import strawberry
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation

import strawberry_django
from tests import models, utils


@strawberry_django.filters.filter(models.Color, lookups=True)
class ColorFilter:
    id: auto
    name: auto


@strawberry_django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
    color: ColorFilter


@strawberry.enum
class FruitEnum(Enum):
    strawberry = "strawberry"
    banana = "banana"


@strawberry_django.filters.filter(models.Fruit)
class EnumFiler:
    name: FruitEnum


@strawberry.input
class NonFilter:
    name: FruitEnum

    def filter(self, queryset):
        raise NotImplementedError


@strawberry_django.filters.filter(models.Fruit)
class FieldFilter:
    search: str

    def filter_search(self, queryset):
        return queryset.filter(name__icontains=self.search)


@strawberry_django.filters.filter(models.Fruit)
class TypeFilter:
    name: auto

    def filter(self, queryset):
        if self.name:
            queryset = queryset.filter(name__icontains=self.name)
        return queryset


@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    id: auto
    name: auto


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field()
    field_filter: List[Fruit] = strawberry_django.field(filters=FieldFilter)
    type_filter: List[Fruit] = strawberry_django.field(filters=TypeFilter)
    enum_filter: List[Fruit] = strawberry_django.field(filters=EnumFiler)


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_field_filter_definition():
    from strawberry_django.fields.field import StrawberryDjangoField

    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(Fruit))
    assert field.get_filters() == FruitFilter
    field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(Fruit), filters=None
    )
    assert field.get_filters() is None


def test_without_filtering(query, fruits):
    result = query("{ fruits { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
        {"id": "3", "name": "banana"},
    ]


def test_exact(query, fruits):
    result = query('{ fruits(filters: { name: { exact: "strawberry" } }) { id name } }')
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]


def test_lt_gt(query, fruits):
    result = query("{ fruits(filters: { id: { gt: 1, lt: 3 } }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "2", "name": "raspberry"},
    ]


def test_in_list(query, fruits):
    result = query("{ fruits(filters: { id: { inList: [ 1, 3 ] } }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "3", "name": "banana"},
    ]


def test_relationship(query, fruits):
    color = models.Color.objects.create(name="red")
    color.fruits.set([fruits[0], fruits[1]])

    result = query(
        '{ fruits(filters: { color: { name: { iExact: "RED" } } })' " { id name } }"
    )
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
    ]


def test_field_filter_method(query, fruits):
    result = query('{ fruits: fieldFilter(filters: { search: "berry" }) { id name } }')
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
        {"id": "2", "name": "raspberry"},
    ]


def test_type_filter_method(query, fruits):
    result = query('{ fruits: typeFilter(filters: { name: "anana" }) { id name } }')
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana"},
    ]


def test_resolver_filter(fruits):
    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(filters: FruitFilter) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return strawberry_django.filters.apply(filters, queryset)

    query = utils.generate_query(Query)
    result = query('{ fruits(filters: { name: { exact: "strawberry" } }) { id name } }')
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]


def test_resolver_filter_with_info(fruits):
    from strawberry.types.info import Info

    @strawberry_django.filters.filter(models.Fruit, lookups=True)
    class FruitFilterWithInfo:
        id: auto
        name: auto
        custom_field: bool

        def filter_custom_field(self, queryset, info: Info):
            # Test here is to prove that info can be passed properly
            assert isinstance(info, Info)
            return queryset.filter(name="banana")

    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(filters: FruitFilterWithInfo, info: Info) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return strawberry_django.filters.apply(filters, queryset, info=info)

    query = utils.generate_query(Query)
    result = query("{ fruits(filters: { customField: true }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana"},
    ]


def test_resolver_filter_override_with_info(fruits):
    from strawberry.types.info import Info

    @strawberry_django.filters.filter(models.Fruit, lookups=True)
    class FruitFilterWithInfo:
        custom_field: bool

        def filter(self, queryset, info: Info):
            # Test here is to prove that info can be passed properly
            assert isinstance(info, Info)
            return queryset.filter(name="banana")

    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(filters: FruitFilterWithInfo, info: Info) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return strawberry_django.filters.apply(filters, queryset, info=info)

    query = utils.generate_query(Query)
    result = query("{ fruits(filters: { customField: true }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "3", "name": "banana"},
    ]


def test_resolver_nonfilter(fruits):
    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(filters: NonFilter) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return strawberry_django.filters.apply(filters, queryset)

    query = utils.generate_query(Query)
    result = query("{ fruits(filters: { name: strawberry } ) { id name } }")
    assert not result.errors


def test_enum(query, fruits):
    result = query("{ fruits: enumFilter(filters: { name: strawberry }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]
