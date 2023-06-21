import datetime
import decimal
import enum
import uuid
from typing import Dict, List, Tuple, Union, cast

import django
import pytest
import strawberry
from django.conf import settings
from django.db import models
from strawberry import auto
from strawberry.enum import EnumDefinition, EnumValue
from strawberry.scalars import JSON
from strawberry.type import StrawberryContainer, StrawberryList, StrawberryOptional

import strawberry_django
from strawberry_django import fields
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.utils import (
    WithStrawberryDjangoObjectDefinition,
    WithStrawberryObjectDefinition,
)


class FieldTypesModel(models.Model):
    boolean = models.BooleanField()
    char = models.CharField(max_length=50)
    date = models.DateField()
    date_time = models.DateTimeField()
    decimal = models.DecimalField()
    email = models.EmailField()
    file = models.FileField()
    file_path = models.FilePathField()
    float = models.FloatField()
    generic_ip_address = models.GenericIPAddressField()
    integer = models.IntegerField()
    image = models.ImageField()
    # NullBooleanField was deprecated and will soon be removed
    null_boolean = (
        models.NullBooleanField()  # type: ignore
        if hasattr(models, "NullBooleanField")
        else models.BooleanField(null=True)
    )
    positive_big_integer = models.PositiveBigIntegerField()
    positive_integer = models.PositiveIntegerField()
    positive_small_integer = models.PositiveSmallIntegerField()
    slug = models.SlugField()
    small_integer = models.SmallIntegerField()
    text = models.TextField()
    time = models.TimeField()
    url = models.URLField()
    uuid = models.UUIDField()
    json = models.JSONField()
    foreign_key = models.ForeignKey(
        "FieldTypesModel",
        blank=True,
        related_name="related_foreign_key",
        on_delete=models.CASCADE,
    )
    one_to_one = models.OneToOneField(
        "FieldTypesModel",
        blank=True,
        related_name="related_one_to_one",
        on_delete=models.CASCADE,
    )
    many_to_many = models.ManyToManyField(
        "FieldTypesModel",
        related_name="related_many_to_many",
    )


def test_field_types():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        id: auto
        boolean: auto
        char: auto
        date: auto
        date_time: auto
        decimal: auto
        email: auto
        file: auto
        file_path: auto
        float: auto
        generic_ip_address: auto
        integer: auto
        image: auto
        null_boolean: auto
        positive_big_integer: auto
        positive_integer: auto
        positive_small_integer: auto
        slug: auto
        small_integer: auto
        text: auto
        time: auto
        url: auto
        uuid: auto
        json: auto

    assert [(f.name, f.type) for f in fields(Type)] == [
        ("id", strawberry.ID),
        ("boolean", bool),
        ("char", str),
        ("date", datetime.date),
        ("date_time", datetime.datetime),
        ("decimal", decimal.Decimal),
        ("email", str),
        ("file", strawberry_django.DjangoFileType),
        ("file_path", str),
        ("float", float),
        ("generic_ip_address", str),
        ("integer", int),
        ("image", strawberry_django.DjangoImageType),
        ("null_boolean", StrawberryOptional(bool)),
        ("positive_big_integer", int),
        ("positive_integer", int),
        ("positive_small_integer", int),
        ("slug", str),
        ("small_integer", int),
        ("text", str),
        ("time", datetime.time),
        ("url", str),
        ("uuid", uuid.UUID),
        ("json", JSON),
    ]


def test_subset_of_fields():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        id: auto
        integer: auto
        text: auto

    assert [(f.name, f.type) for f in fields(Type)] == [
        ("id", strawberry.ID),
        ("integer", int),
        ("text", str),
    ]


def test_type_extension():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        char: auto
        text: bytes  # override type

        @strawberry.field
        @staticmethod
        def my_field() -> int:
            return 0

    assert [(f.name, f.type) for f in fields(Type)] == [
        ("char", str),
        ("text", bytes),
        ("my_field", int),
    ]


def test_field_does_not_exist():
    with pytest.raises(django.core.exceptions.FieldDoesNotExist):

        @strawberry_django.type(FieldTypesModel)
        class Type:
            unknown_field: auto


def test_override_field_type():
    @strawberry.enum
    class EnumType(enum.Enum):
        a = "A"

    @strawberry_django.type(FieldTypesModel)
    class Type:
        char: EnumType

    assert [(f.name, f.type) for f in fields(Type)] == [
        (
            "char",
            EnumDefinition(
                wrapped_cls=EnumType,
                name="EnumType",
                values=[EnumValue(name="a", value="A")],
                description=None,
            ),
        ),
    ]


def test_override_field_default_value():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        char: str = "my value"

    assert [(f.name, f.type) for f in fields(Type)] == [
        ("char", str),
    ]

    assert Type().char == "my value"


def test_related_fields():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        foreign_key: auto
        one_to_one: auto
        many_to_many: auto
        related_foreign_key: auto
        related_one_to_one: auto
        related_many_to_many: auto

    assert [(f.name, f.type, f.is_list) for f in fields(Type)] == [
        ("foreign_key", strawberry_django.DjangoModelType, False),
        ("one_to_one", strawberry_django.DjangoModelType, False),
        (
            "many_to_many",
            StrawberryList(strawberry_django.DjangoModelType),
            True,
        ),
        (
            "related_foreign_key",
            StrawberryList(strawberry_django.DjangoModelType),
            True,
        ),
        (
            "related_one_to_one",
            StrawberryOptional(strawberry_django.DjangoModelType),
            False,
        ),
        (
            "related_many_to_many",
            StrawberryList(strawberry_django.DjangoModelType),
            True,
        ),
    ]


def test_related_input_fields():
    @strawberry_django.input(FieldTypesModel)
    class Input:
        foreign_key: auto
        one_to_one: auto
        many_to_many: auto
        related_foreign_key: auto
        related_one_to_one: auto
        related_many_to_many: auto

    expected_fields: Dict[str, Tuple[Union[type, StrawberryContainer], bool]] = {
        "foreign_key": (
            strawberry_django.OneToManyInput,
            True,
        ),
        "one_to_one": (
            strawberry_django.OneToOneInput,
            True,
        ),
        "many_to_many": (
            strawberry_django.ManyToManyInput,
            True,
        ),
        "related_foreign_key": (
            strawberry_django.ManyToOneInput,
            True,
        ),
        "related_one_to_one": (
            strawberry_django.OneToOneInput,
            True,
        ),
        "related_many_to_many": (
            strawberry_django.ManyToManyInput,
            True,
        ),
    }

    all_fields = fields(cast(WithStrawberryDjangoObjectDefinition, Input))
    assert len(all_fields) == len(expected_fields)

    for f in all_fields:
        expected_type, expected_is_optional = expected_fields[f.name]
        assert isinstance(f, StrawberryDjangoField)
        assert f.is_optional == expected_is_optional
        assert isinstance(f.type, StrawberryOptional)
        assert f.type.of_type == expected_type


@pytest.mark.skipif(
    not settings.GEOS_IMPORTED,
    reason="Test requires GEOS to be imported and properly configured",
)
def test_geos_fields():
    from strawberry_django.fields import types
    from tests.models import GeosFieldsModel

    @strawberry_django.type(GeosFieldsModel)
    class GeoFieldType:
        point: auto
        line_string: auto
        polygon: auto
        multi_point: auto
        multi_line_string: auto
        multi_polygon: auto

    assert [
        (f.name, cast(StrawberryOptional, f.type).of_type)
        for f in fields(cast(WithStrawberryObjectDefinition, GeoFieldType))
    ] == [
        ("point", types.Point),
        ("line_string", types.LineString),
        ("polygon", types.Polygon),
        ("multi_point", types.MultiPoint),
        ("multi_line_string", types.MultiLineString),
        ("multi_polygon", types.MultiPolygon),
    ]


def test_inherit_type():
    global Type

    @strawberry_django.type(FieldTypesModel)
    class Base:
        char: auto
        one_to_one: "Type"

    @strawberry_django.type(FieldTypesModel)
    class Type(Base):
        many_to_many: List["Type"]

    assert [(f.name, f.type) for f in fields(Type)] == [
        ("char", str),
        ("one_to_one", Type),
        ("many_to_many", StrawberryList(Type)),
    ]


def test_inherit_input():
    global Type

    @strawberry_django.type(FieldTypesModel)
    class Type:
        char: auto
        one_to_one: "Type"
        many_to_many: List["Type"]

    @strawberry_django.input(FieldTypesModel)
    class Input(Type):
        id: auto
        my_data: str

    assert [(f.name, f.type) for f in fields(Input)] == [
        ("char", str),
        ("one_to_one", StrawberryOptional(strawberry_django.OneToOneInput)),
        (
            "many_to_many",
            StrawberryOptional(strawberry_django.ManyToManyInput),
        ),
        ("id", StrawberryOptional(strawberry.ID)),
        ("my_data", str),
    ]


def test_inherit_partial_input():
    global Type

    @strawberry_django.type(FieldTypesModel)
    class Type:
        char: auto
        one_to_one: "Type"

    @strawberry_django.input(FieldTypesModel)
    class Input(Type):
        pass

    @strawberry_django.input(FieldTypesModel, partial=True)
    class PartialInput(Input):
        pass

    assert [(f.name, f.type, f.is_optional) for f in fields(PartialInput)] == [
        ("char", StrawberryOptional(str), True),
        (
            "one_to_one",
            StrawberryOptional(strawberry_django.OneToOneInput),
            True,
        ),
    ]


def test_notimplemented():
    """Test that an unrecognized field raises `NotImplementedError`."""

    class UnknownField(models.Field):
        """A field unknown to Strawberry."""

    class UnknownModel(models.Model):
        """A model with UnknownField."""

        field = UnknownField()

    @strawberry_django.type(UnknownModel)
    class UnknownType:
        field: auto

    @strawberry.type
    class Query:
        unknown_type: UnknownType

    with pytest.raises(TypeError, match=r"UnknownModel\.field"):
        strawberry.Schema(query=Query)
