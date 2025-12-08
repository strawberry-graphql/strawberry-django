import dataclasses
from typing import cast

import strawberry
from strawberry import auto
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryOptional
from strawberry.types.maybe import Maybe

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


def test_maybe_field_default_value():
    @strawberry_django.input(TypeModel)
    class InputWithMaybe:
        my_maybe_field: Maybe[bool]
        regular_optional_field: str | None

    @strawberry.input
    class StrawberryInputWithMaybe:
        my_maybe_field: Maybe[bool]

    django_fields = {f.name: f for f in dataclasses.fields(InputWithMaybe)}
    strawberry_fields = {
        f.name: f for f in dataclasses.fields(StrawberryInputWithMaybe)
    }

    assert django_fields["my_maybe_field"].default is None
    assert (
        django_fields["my_maybe_field"].default
        == strawberry_fields["my_maybe_field"].default
    )

    assert django_fields["regular_optional_field"].default is strawberry.UNSET
