from typing import cast

import strawberry
from strawberry import auto
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryOptional

import strawberry_django

from .test_type import TypeModel


def test_input():
    @strawberry_django.input(TypeModel)
    class Input:
        id: auto
        boolean: auto
        string: auto

    object_definition = get_object_definition(Input, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("id", StrawberryOptional(cast("type", strawberry.ID))),
        ("boolean", bool),
        ("string", str),
    ]


def test_inherit(testtype):
    @testtype(TypeModel)
    class Base:
        id: auto
        boolean: auto

    @strawberry_django.input(TypeModel)
    class Input(Base):
        string: auto

    object_definition = get_object_definition(Input, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("id", StrawberryOptional(cast("type", strawberry.ID))),
        ("boolean", bool),
        ("string", str),
    ]


def test_relationship(testtype):
    @strawberry_django.input(TypeModel)
    class Input:
        foreign_key: auto
        related_foreign_key: auto
        one_to_one: auto
        related_one_to_one: auto
        many_to_many: auto
        related_many_to_many: auto

    object_definition = get_object_definition(Input, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("foreign_key", StrawberryOptional(strawberry_django.OneToManyInput)),
        (
            "related_foreign_key",
            StrawberryOptional(strawberry_django.ManyToOneInput),
        ),
        ("one_to_one", StrawberryOptional(strawberry_django.OneToOneInput)),
        (
            "related_one_to_one",
            StrawberryOptional(strawberry_django.OneToOneInput),
        ),
        (
            "many_to_many",
            StrawberryOptional(strawberry_django.ManyToManyInput),
        ),
        (
            "related_many_to_many",
            StrawberryOptional(strawberry_django.ManyToManyInput),
        ),
    ]


def test_relationship_inherit(testtype):
    @testtype(TypeModel)
    class Base:
        foreign_key: auto
        related_foreign_key: auto
        one_to_one: auto
        related_one_to_one: auto
        many_to_many: auto
        related_many_to_many: auto
        another_name: auto = strawberry_django.field(field_name="foreign_key")

    @strawberry_django.input(TypeModel)
    class Input(Base):
        pass

    object_definition = get_object_definition(Input, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("foreign_key", StrawberryOptional(strawberry_django.OneToManyInput)),
        (
            "related_foreign_key",
            StrawberryOptional(strawberry_django.ManyToOneInput),
        ),
        ("one_to_one", StrawberryOptional(strawberry_django.OneToOneInput)),
        (
            "related_one_to_one",
            StrawberryOptional(strawberry_django.OneToOneInput),
        ),
        (
            "many_to_many",
            StrawberryOptional(strawberry_django.ManyToManyInput),
        ),
        (
            "related_many_to_many",
            StrawberryOptional(strawberry_django.ManyToManyInput),
        ),
        ("another_name", StrawberryOptional(strawberry_django.OneToManyInput)),
    ]
