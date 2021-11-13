from typing import List

import pytest
import strawberry
from strawberry.annotation import StrawberryAnnotation

import strawberry_django
from strawberry_django import auto
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
