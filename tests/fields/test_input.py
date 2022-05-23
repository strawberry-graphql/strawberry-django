import strawberry
from django.db import models
from strawberry import auto
from strawberry.type import StrawberryOptional

import strawberry_django


class InputFieldsModel(models.Model):
    mandatory = models.IntegerField()
    default = models.IntegerField(default=1)
    blank = models.IntegerField(blank=True)
    null = models.IntegerField(null=True)
    null_boolean = models.NullBooleanField()


def test_input_type():
    @strawberry_django.input(InputFieldsModel)
    class InputType:
        id: auto
        mandatory: auto
        default: auto
        blank: auto
        null: auto
        null_boolean: auto

    assert [(f.name, f.type) for f in InputType._type_definition.fields] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("mandatory", int),
        ("default", StrawberryOptional(int)),
        ("blank", StrawberryOptional(int)),
        ("null", StrawberryOptional(int)),
        ("null_boolean", StrawberryOptional(bool)),
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

    assert [(f.name, f.type) for f in InputType._type_definition.fields] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("mandatory", StrawberryOptional(int)),
        ("default", StrawberryOptional(int)),
        ("blank", StrawberryOptional(int)),
        ("null", StrawberryOptional(int)),
        ("null_boolean", StrawberryOptional(bool)),
    ]


def test_input_type_basic():
    from .. import models

    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    assert [(f.name, f.type) for f in UserInput._type_definition.fields] == [
        ("name", str),
    ]


def test_partial_input_type():
    from .. import models

    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput:
        name: auto

    assert [(f.name, f.type) for f in UserPartialInput._type_definition.fields] == [
        ("name", StrawberryOptional(str)),
    ]


def test_partial_input_type_inheritance():
    from .. import models

    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput(UserInput):
        pass

    assert [(f.name, f.type) for f in UserPartialInput._type_definition.fields] == [
        ("name", StrawberryOptional(str)),
    ]


def test_input_type_inheritance_from_type():
    from .. import models

    @strawberry_django.type(models.User)
    class User:
        id: auto
        name: auto

    @strawberry_django.input(models.User)
    class UserInput(User):
        pass

    assert [(f.name, f.type) for f in UserInput._type_definition.fields] == [
        ("id", StrawberryOptional(strawberry.ID)),
        ("name", str),
    ]
