from typing import Optional

import pytest
import strawberry
from strawberry import auto
from strawberry.type import StrawberryOptional, get_object_definition

import strawberry_django
from strawberry_django.filters import DjangoModelFilterInput
from strawberry_django.settings import strawberry_django_settings
from tests import models


@pytest.fixture(autouse=True)
def _filter_order_settings(settings):
    settings.STRAWBERRY_DJANGO = {
        **strawberry_django_settings(),
        "USE_DEPRECATED_FILTERS": True,
    }


def test_filter():
    @strawberry_django.filters.filter(models.Fruit)
    class Filter:
        id: auto
        name: auto
        color: auto
        types: auto

    object_definition = get_object_definition(Filter, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("name", StrawberryOptional(str)),
        ("color", StrawberryOptional(DjangoModelFilterInput)),
        ("types", StrawberryOptional(DjangoModelFilterInput)),
        ("AND", StrawberryOptional(Filter)),
        ("OR", StrawberryOptional(Filter)),
        ("NOT", StrawberryOptional(Filter)),
        ("DISTINCT", StrawberryOptional(bool)),
    ]


def test_lookups():
    @strawberry_django.filters.filter(models.Fruit, lookups=True)
    class Filter:
        id: auto
        name: auto
        color: auto
        types: auto

    object_definition = get_object_definition(Filter, strict=True)
    assert [
        (f.name, f.type.of_type.__name__)  # type: ignore
        for f in object_definition.fields
    ] == [
        ("id", "FilterLookup"),
        ("name", "FilterLookup"),
        ("color", "DjangoModelFilterInput"),
        ("types", "DjangoModelFilterInput"),
        ("AND", "Filter"),
        ("OR", "Filter"),
        ("NOT", "Filter"),
        ("DISTINCT", "bool"),
    ]


def test_inherit(testtype):
    @testtype(models.Fruit)
    class Base:
        id: auto
        name: auto
        color: auto
        types: auto

    @strawberry_django.filters.filter(models.Fruit)
    class Filter(Base):
        pass

    object_definition = get_object_definition(Filter, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("name", StrawberryOptional(str)),
        ("color", StrawberryOptional(DjangoModelFilterInput)),
        ("types", StrawberryOptional(DjangoModelFilterInput)),
        ("AND", StrawberryOptional(Filter)),
        ("OR", StrawberryOptional(Filter)),
        ("NOT", StrawberryOptional(Filter)),
        ("DISTINCT", StrawberryOptional(bool)),
    ]


def test_relationship():
    @strawberry_django.filters.filter(models.Color)
    class ColorFilter:
        name: auto

    @strawberry_django.filters.filter(models.Fruit)
    class Filter:
        color: Optional[ColorFilter]

    object_definition = get_object_definition(Filter, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("color", StrawberryOptional(ColorFilter)),
        ("AND", StrawberryOptional(Filter)),
        ("OR", StrawberryOptional(Filter)),
        ("NOT", StrawberryOptional(Filter)),
        ("DISTINCT", StrawberryOptional(bool)),
    ]


def test_relationship_with_inheritance():
    @strawberry_django.filters.filter(models.Color)
    class ColorFilter:
        name: auto

    @strawberry_django.type(models.Fruit)
    class Base:
        color: auto

    @strawberry_django.filters.filter(models.Fruit)
    class Filter(Base):
        color: Optional[ColorFilter]

    object_definition = get_object_definition(Filter, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("color", StrawberryOptional(ColorFilter)),
        ("AND", StrawberryOptional(Filter)),
        ("OR", StrawberryOptional(Filter)),
        ("NOT", StrawberryOptional(Filter)),
        ("DISTINCT", StrawberryOptional(bool)),
    ]
