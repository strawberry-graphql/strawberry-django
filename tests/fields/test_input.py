import strawberry
import strawberry_django
from strawberry_django import auto
from django.db import models


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

    assert [(f.name, f.type, f.is_optional) for f in InputType._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('mandatory', int, False),
        ('default', int , True),
        ('blank', int, True),
        ('null', int, True),
        ('null_boolean', bool, True),
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

    assert [(f.name, f.type, f.is_optional) for f in InputType._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('mandatory', int, True),
        ('default', int , True),
        ('blank', int, True),
        ('null', int, True),
        ('null_boolean', bool, True),
    ]

def test_input_type():
    from .. import models
    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    assert [(f.name, f.type, f.is_optional) for f in UserInput._type_definition.fields] == [
        ('name', str, False),
    ]

def test_partial_input_type():
    from .. import models
    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput:
        name: auto

    assert [(f.name, f.type, f.is_optional) for f in UserPartialInput._type_definition.fields] == [
        ('name', str, True),
    ]


def test_partial_input_type_inheritance():
    from .. import models
    @strawberry_django.input(models.User)
    class UserInput:
        name: auto

    @strawberry_django.input(models.User, partial=True)
    class UserPartialInput(UserInput):
        pass

    assert [(f.name, f.type, f.is_optional) for f in UserPartialInput._type_definition.fields] == [
        ('name', str, True),
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

    assert [(f.name, f.type, f.is_optional) for f in UserInput._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('name', str, False),
    ]
