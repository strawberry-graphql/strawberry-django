import datetime
import decimal
import enum
import uuid
from typing import Dict, List, Tuple, Union, cast

import pytest
import strawberry
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from strawberry import auto
from strawberry.enum import EnumDefinition, EnumValue
from strawberry.scalars import JSON
from strawberry.type import (
    StrawberryContainer,
    StrawberryList,
    StrawberryOptional,
    get_object_definition,
)

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField


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
    array_of_boolean = ArrayField(models.BooleanField())
    array_of_char = ArrayField(models.CharField(max_length=50))
    array_of_date = ArrayField(models.DateField())
    array_of_date_time = ArrayField(models.DateTimeField())
    array_of_decimal = ArrayField(models.DecimalField())
    array_of_email = ArrayField(models.EmailField())
    array_of_file = ArrayField(models.FileField())
    array_of_file_path = ArrayField(models.FilePathField())
    array_of_float = ArrayField(models.FloatField())
    array_of_generic_ip_address = ArrayField(models.GenericIPAddressField())
    array_of_integer = ArrayField(models.IntegerField())
    array_of_image = ArrayField(models.ImageField())
    # NullBooleanField was deprecated and will soon be removed
    array_of_null_boolean = ArrayField(
        (
            models.NullBooleanField()  # type: ignore
            if hasattr(models, "NullBooleanField")
            else models.BooleanField(null=True)
        ),
    )
    array_of_positive_big_integer = ArrayField(models.PositiveBigIntegerField())
    array_of_positive_integer = ArrayField(models.PositiveIntegerField())
    array_of_positive_small_integer = ArrayField(models.PositiveSmallIntegerField())
    array_of_slug = ArrayField(models.SlugField())
    array_of_small_integer = ArrayField(models.SmallIntegerField())
    array_of_text = ArrayField(models.TextField())
    array_of_time = ArrayField(models.TimeField())
    array_of_url = ArrayField(models.URLField())
    array_of_uuid = ArrayField(models.UUIDField())
    array_of_json = ArrayField(models.JSONField())
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
        array_of_boolean: auto
        array_of_char: auto
        array_of_date: auto
        array_of_date_time: auto
        array_of_decimal: auto
        array_of_email: auto
        array_of_file: auto
        array_of_file_path: auto
        array_of_float: auto
        array_of_generic_ip_address: auto
        array_of_integer: auto
        array_of_image: auto
        array_of_null_boolean: auto
        array_of_positive_big_integer: auto
        array_of_positive_integer: auto
        array_of_positive_small_integer: auto
        array_of_slug: auto
        array_of_small_integer: auto
        array_of_text: auto
        array_of_time: auto
        array_of_url: auto
        array_of_uuid: auto
        array_of_json: auto

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
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
        ("array_of_boolean", List[bool]),
        ("array_of_char", List[str]),
        ("array_of_date", List[datetime.date]),
        ("array_of_date_time", List[datetime.datetime]),
        ("array_of_decimal", List[decimal.Decimal]),
        ("array_of_email", List[str]),
        ("array_of_file", List[strawberry_django.DjangoFileType]),
        ("array_of_file_path", List[str]),
        ("array_of_float", List[float]),
        ("array_of_generic_ip_address", List[str]),
        ("array_of_integer", List[int]),
        ("array_of_image", List[strawberry_django.DjangoImageType]),
        ("array_of_null_boolean", List[StrawberryOptional(bool)]),
        ("array_of_positive_big_integer", List[int]),
        ("array_of_positive_integer", List[int]),
        ("array_of_positive_small_integer", List[int]),
        ("array_of_slug", List[str]),
        ("array_of_small_integer", List[int]),
        ("array_of_text", List[str]),
        ("array_of_time", List[datetime.time]),
        ("array_of_url", List[str]),
        ("array_of_uuid", List[uuid.UUID]),
        ("array_of_json", List[JSON]),
    ]


def test_subset_of_fields():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        id: auto
        integer: auto
        text: auto

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
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

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("char", str),
        ("text", bytes),
        ("my_field", int),
    ]


def test_field_does_not_exist():
    with pytest.raises(FieldDoesNotExist):

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

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
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

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
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

    object_definition = get_object_definition(Type, strict=True)
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_list)
        for f in object_definition.fields
    ] == [
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

    object_definition = get_object_definition(Input, strict=True)
    assert len(object_definition.fields) == len(expected_fields)

    for f in object_definition.fields:
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

    object_definition = get_object_definition(GeoFieldType, strict=True)
    assert [
        (f.name, cast(StrawberryOptional, f.type).of_type)
        for f in object_definition.fields
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
        one_to_one: "Type"  # type: ignore

    @strawberry_django.type(FieldTypesModel)
    class Type(Base):  # type: ignore
        many_to_many: List["Type"]  # type: ignore

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("char", str),
        ("one_to_one", Type),
        ("many_to_many", StrawberryList(Type)),
    ]


def test_inherit_input():
    global Type

    @strawberry_django.type(FieldTypesModel)
    class Type:  # type: ignore
        char: auto
        one_to_one: "Type"
        many_to_many: List["Type"]

    @strawberry_django.input(FieldTypesModel)
    class Input(Type):
        id: auto
        my_data: str

    object_definition = get_object_definition(Input, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
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

    object_definition = get_object_definition(PartialInput, strict=True)
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_optional)
        for f in object_definition.fields
    ] == [
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
