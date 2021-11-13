import pytest
import strawberry
from django.db import models
from strawberry.type import StrawberryList, StrawberryOptional

import strawberry_django
from strawberry_django import TypeRegister
from strawberry_django.legacy.types import LazyModelType


@pytest.fixture
def types():
    types = strawberry_django.TypeRegister()
    return types


class Child(models.Model):
    child = models.ForeignKey("Child", on_delete=models.CASCADE)


class Model(models.Model):
    string = models.TextField()
    integer = models.IntegerField()
    foreign_key = models.ForeignKey(Child, on_delete=models.CASCADE)
    one_to_one = models.OneToOneField(Child, on_delete=models.CASCADE)
    many_to_many = models.ManyToManyField(Child)


def test_field_name(types):
    @types.register("string")
    class string(str):
        pass

    @strawberry_django.type(Model, fields=["string", "integer"], types=types)
    class Type:
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ("string", string),
        ("integer", int),
    ]


def test_field_type(types):
    @types.register(models.IntegerField)
    class integer(int):
        pass

    @strawberry_django.type(Model, fields=["string", "integer"], types=types)
    class Type:
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ("string", str),
        ("integer", integer),
    ]


def test_model(types):
    @types.register(Child)
    @strawberry_django.type(Child, fields=["id"])
    class ChildType:
        pass

    @strawberry_django.type(
        Model,
        fields=[
            "foreign_key",
            "one_to_one",
            "many_to_many",
        ],
        types=types,
    )
    class Type:
        pass

    assert [(f.name, f.type or f.child.type) for f in Type._type_definition.fields] == [
        ("foreign_key", ChildType),
        ("one_to_one", ChildType),
        ("many_to_many", StrawberryList(ChildType)),
    ]


def test_self_reference(types):
    @types.register
    @strawberry_django.type(Child, fields=["child"], types=types)
    class Type:
        pass

    assert [(f.name, f.type or f.child.type) for f in Type._type_definition.fields] == [
        (
            "child",
            StrawberryOptional(
                StrawberryList(LazyModelType(Child.child.field, TypeRegister, False))
            ),
        ),
    ]


def test_model_shortcut(types):
    @types.register
    @strawberry_django.type(Child, fields=["id"])
    class ChildType:
        pass

    @strawberry_django.type(
        Model,
        fields=[
            "foreign_key",
        ],
        types=types,
    )
    class Type:
        pass

    assert [(f.name, f.type or f.child.type) for f in Type._type_definition.fields] == [
        ("foreign_key", ChildType),
    ]


def test_no_type_for_field(types):
    class MyField(models.TextField):
        pass

    class MyModel(models.Model):
        field = MyField()

    with pytest.raises(TypeError, match="No type defined for 'MyField'"):

        @strawberry_django.type(MyModel, types=types)
        class Type:
            pass


def test_no_type_for_model(types):
    with pytest.raises(
        TypeError,
        match="No type defined for field 'ForeignKey'"
        " which has related model 'Child'",
    ):

        @strawberry_django.type(Model, types=types)
        class Type:
            pass

        # trigger lazy evaluation
        [
            f.type.resolve_type()
            for f in Type._type_definition.fields
            if isinstance(f.type, LazyModelType)
        ]


def test_input_and_output_types(types):
    @types.register(Child)
    @strawberry_django.type(Child, fields=["id"])
    class ChildType:
        pass

    @types.register(Child)
    @strawberry_django.input(Child, fields=["id"])
    class ChildInput:
        pass

    @strawberry_django.type(
        Model,
        fields=[
            "foreign_key",
        ],
        types=types,
    )
    class Type:
        pass

    @strawberry_django.input(
        Model,
        fields=[
            "foreign_key",
        ],
        types=types,
    )
    class Input:
        pass

    assert [(f.name, f.type or f.child.type) for f in Type._type_definition.fields] == [
        ("foreign_key", ChildType),
    ]

    assert [
        (f.name, f.type or f.child.type) for f in Input._type_definition.fields
    ] == [
        ("foreign_key_id", strawberry.ID),
    ]
