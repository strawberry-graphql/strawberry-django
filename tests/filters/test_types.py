import strawberry
from strawberry.type import StrawberryOptional

import strawberry_django
from strawberry_django import auto, fields
from strawberry_django.filters import DjangoModelFilterInput

from .. import models


def test_filter():
    @strawberry_django.filters.filter(models.Fruit)
    class Filter:
        id: auto
        name: auto
        color: auto
        types: auto

    assert [(f.name, f.type) for f in fields(Filter)] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("name", StrawberryOptional(str)),
        ("color", StrawberryOptional(DjangoModelFilterInput)),
        ("types", StrawberryOptional(DjangoModelFilterInput)),
    ]


def test_lookups():
    @strawberry_django.filters.filter(models.Fruit, lookups=True)
    class Filter:
        id: auto
        name: auto
        color: auto
        types: auto

    assert [(f.name, f.type.of_type.__name__) for f in fields(Filter)] == [
        ("id", "IDFilterLookup"),
        ("name", "StrFilterLookup"),
        ("color", "DjangoModelFilterInput"),
        ("types", "DjangoModelFilterInput"),
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

    assert [(f.name, f.type) for f in fields(Filter)] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("name", StrawberryOptional(str)),
        ("color", StrawberryOptional(DjangoModelFilterInput)),
        ("types", StrawberryOptional(DjangoModelFilterInput)),
    ]


def test_relationship():
    @strawberry_django.filters.filter(models.Color)
    class ColorFilter:
        name: auto

    @strawberry_django.filters.filter(models.Fruit)
    class Filter:
        color: ColorFilter

    assert [(f.name, f.type) for f in fields(Filter)] == [
        ("color", StrawberryOptional(ColorFilter)),
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
        color: ColorFilter

    assert [(f.name, f.type) for f in fields(Filter)] == [
        ("color", StrawberryOptional(ColorFilter)),
    ]
