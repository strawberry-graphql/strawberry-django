import strawberry
from django.db import models
from strawberry import auto
from strawberry.type import StrawberryOptional, get_object_definition_strict

import strawberry_django


class InputFieldsModel(models.Model):
    mandatory = models.IntegerField()
    default = models.IntegerField(default=1)
    blank = models.IntegerField(blank=True)
    null = models.IntegerField(null=True)
    # NullBoleanField is deprecated and will be removed in Django 5.0
    null_boolean = (
        models.NullBooleanField()  # type: ignore
        if hasattr(models, "NullBooleanField")
        else models.BooleanField(null=True)
    )


def test_input_type():
    @strawberry_django.input(InputFieldsModel)
    class InputType:
        id: auto
        mandatory: auto
        default: auto
        blank: auto
        null: auto
        null_boolean: auto

    assert [
        (f.name, f.type) for f in get_object_definition_strict(InputType).fields
    ] == [
        ("id", StrawberryOptional(strawberry.ID)),  # type: ignore
        ("mandatory", int),
        ("default", StrawberryOptional(int)),  # type: ignore
        ("blank", StrawberryOptional(int)),  # type: ignore
        ("null", StrawberryOptional(int)),  # type: ignore
        ("null_boolean", StrawberryOptional(bool)),  # type: ignore
    ]


def test_input_type_for_partial_update():
    @strawberry_django.input(InputFieldsModel, partial=True)
    class InputType:
        id: auto
        mandatory: auto
        default: auto
        blank: auto
        null: auto
        null_boolean: auto

    assert [
        (f.name, f.type) for f in get_object_definition_strict(InputType).fields
    ] == [
        ("id", StrawberryOptional(strawberry.ID)),  # type: ignore
        ("mandatory", StrawberryOptional(int)),  # type: ignore
        ("default", StrawberryOptional(int)),  # type: ignore
        ("blank", StrawberryOptional(int)),  # type: ignore
        ("null", StrawberryOptional(int)),  # type: ignore
        ("null_boolean", StrawberryOptional(bool)),  # type: ignore
    ]


def test_input_type_basic():
    from tests import models

    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    assert [
        (f.name, f.type) for f in get_object_definition_strict(UserInput).fields
    ] == [
        ("name", str),
    ]


def test_partial_input_type():
    from tests import models

    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput:
        name: auto

    assert [
        (f.name, f.type) for f in get_object_definition_strict(UserPartialInput).fields
    ] == [
        ("name", StrawberryOptional(str)),  # type: ignore
    ]


def test_partial_input_type_inheritance():
    from tests import models

    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput(UserInput):
        pass

    assert [
        (f.name, f.type) for f in get_object_definition_strict(UserPartialInput).fields
    ] == [
        ("name", StrawberryOptional(str)),  # type: ignore
    ]


def test_input_type_inheritance_from_type():
    from tests import models

    @strawberry_django.type(models.User)
    class User:
        id: auto
        name: auto

    @strawberry_django.input(models.User)
    class UserInput(User):
        pass

    assert [
        (f.name, f.type) for f in get_object_definition_strict(UserInput).fields
    ] == [
        ("id", StrawberryOptional(strawberry.ID)),  # type: ignore
        ("name", str),
    ]
