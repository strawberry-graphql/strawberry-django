import datetime, decimal, enum, uuid
import pytest
import strawberry
import strawberry_django
from django.db import models


class FieldTypesModel(models.Model):
    boolean = models.BooleanField()
    char = models.CharField(max_length=50)
    date = models.DateField()
    date_time = models.DateTimeField()
    decimal = models.DecimalField()
    email = models.EmailField()
    file_path = models.FilePathField()
    float = models.FloatField()
    generic_ip_address = models.GenericIPAddressField()
    integer = models.IntegerField()
    null_boolean = models.NullBooleanField()
    positive_big_integer = models.PositiveBigIntegerField()
    positive_integer = models.PositiveIntegerField()
    positive_small_integer = models.PositiveSmallIntegerField()
    slug = models.SlugField()
    small_integer = models.SmallIntegerField()
    text = models.TextField()
    time = models.TimeField()
    url = models.URLField()
    uuid = models.UUIDField()


def test_field_types():
    @strawberry_django.type(FieldTypesModel)
    class Type:
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('id', strawberry.ID),
        ('boolean', bool),
        ('char', str),
        ('date', datetime.date),
        ('date_time', datetime.datetime),
        ('decimal', decimal.Decimal),
        ('email', str),
        ('file_path', str),
        ('float', float),
        ('generic_ip_address', str),
        ('integer', int),
        ('null_boolean', bool),
        ('positive_big_integer', int),
        ('positive_integer', int),
        ('positive_small_integer', int),
        ('slug', str),
        ('small_integer', int),
        ('text', str),
        ('time', datetime.time),
        ('url', str),
        ('uuid', uuid.UUID),
    ]


def test_subset_of_fields():
    @strawberry_django.type(FieldTypesModel, fields=['id', 'integer', 'text'])
    class Type:
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('id', strawberry.ID),
        ('integer', int),
        ('text', str),
    ]


def test_type_extension():
    @strawberry_django.type(FieldTypesModel, fields=['char'])
    class Type:
        text: bytes # override type
        @strawberry.field
        def my_field() -> int:
            return 0

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('text', bytes),
        ('char', str),
        ('my_field', int),
    ]


def test_field_does_not_exist():
    with pytest.raises(AttributeError, match="Django model 'FieldTypesModel' has no field 'unknownField'"):
        @strawberry_django.type(FieldTypesModel, fields=['unknownField'])
        class Type:
            pass

def test_override_field_type():
    @strawberry.enum
    class EnumType(enum.Enum):
        a = 'A'

    @strawberry_django.type(FieldTypesModel, fields=['char'])
    class Type:
        char: EnumType

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('char', EnumType),
    ]

def test_override_field_default_value():
    @strawberry_django.type(FieldTypesModel, fields=['char'])
    class Type:
        char = 'my value'

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('char', str),
    ]

    assert Type().char == 'my value'
