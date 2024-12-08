import datetime
import decimal
import enum
import uuid
from typing import Any, Optional, Union, cast

import django
import pytest
import strawberry
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from strawberry import auto
from strawberry.scalars import JSON
from strawberry.types import get_object_definition
from strawberry.types.base import (
    StrawberryContainer,
    StrawberryList,
    StrawberryOptional,
)
from strawberry.types.enum import EnumDefinition, EnumValue

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.type import _process_type  # noqa: PLC2701

if django.VERSION >= (5, 0):
    from django.db.models import GeneratedField  # type: ignore
else:
    GeneratedField = None


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
    generated_decimal = (
        GeneratedField(
            expression=models.F("decimal") * 2,
            db_persist=True,
            output_field=models.DecimalField(),
        )
        if GeneratedField is not None
        else None
    )
    generated_nullable_decimal = (
        GeneratedField(
            expression=models.F("decimal") * 2,
            db_persist=True,
            output_field=models.DecimalField(null=True, blank=True),
        )
        if GeneratedField is not None
        else None
    )
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

    expected_types: list[tuple[str, Any]] = [
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

    if django.VERSION >= (5, 0):
        Type.__annotations__["generated_decimal"] = auto
        expected_types.append(("generated_decimal", decimal.Decimal))

        Type.__annotations__["generated_nullable_decimal"] = auto
        expected_types.append(("generated_nullable_decimal", Optional[decimal.Decimal]))

    type_to_test = _process_type(Type, model=FieldTypesModel)
    object_definition = get_object_definition(type_to_test, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == expected_types


def test_field_types_for_array_fields():
    class ModelWithArrays(models.Model):
        str_array = ArrayField(models.CharField(max_length=50))
        int_array = ArrayField(models.IntegerField())

    @strawberry_django.type(ModelWithArrays)
    class Type:
        str_array: auto
        int_array: auto

    type_to_test = _process_type(Type, model=ModelWithArrays)
    object_definition = get_object_definition(type_to_test, strict=True)

    str_array_field = object_definition.get_field("str_array")
    assert str_array_field
    assert isinstance(str_array_field.type, StrawberryList)
    assert str_array_field.type.of_type is str

    int_array_field = object_definition.get_field("int_array")
    assert int_array_field
    assert isinstance(int_array_field.type, StrawberryList)
    assert int_array_field.type.of_type is int


def test_field_types_for_matrix_fields():
    class ModelWithMatrixes(models.Model):
        str_matrix = ArrayField(ArrayField(models.CharField(max_length=50)))
        int_matrix = ArrayField(ArrayField(models.IntegerField()))

    @strawberry_django.type(ModelWithMatrixes)
    class Type:
        str_matrix: auto
        int_matrix: auto

    type_to_test = _process_type(Type, model=ModelWithMatrixes)
    object_definition = get_object_definition(type_to_test, strict=True)

    str_matrix_field = object_definition.get_field("str_matrix")
    assert str_matrix_field
    assert isinstance(str_matrix_field.type, StrawberryList)
    assert isinstance(str_matrix_field.type.of_type, StrawberryList)
    assert str_matrix_field.type.of_type.of_type is str

    int_matrix_field = object_definition.get_field("int_matrix")
    assert int_matrix_field
    assert isinstance(int_matrix_field.type, StrawberryList)
    assert isinstance(int_matrix_field.type.of_type, StrawberryList)
    assert int_matrix_field.type.of_type.of_type is int


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
        (f.name, f.type, cast("StrawberryDjangoField", f).is_list)
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

    expected_fields: dict[str, tuple[Union[type, StrawberryContainer], bool]] = {
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
        (f.name, cast("StrawberryOptional", f.type).of_type)
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
        one_to_one: "Type"

    @strawberry_django.type(FieldTypesModel)
    class Type(Base):  # type: ignore
        many_to_many: list["Type"]

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
        many_to_many: list["Type"]

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
        (f.name, f.type, cast("StrawberryDjangoField", f).is_optional)
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
