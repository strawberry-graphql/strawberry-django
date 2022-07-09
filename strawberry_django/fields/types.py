import datetime
import decimal
import uuid
from typing import List, Optional

import django
import strawberry
from django.db.models import fields
from django.db.models.fields.reverse_related import ForeignObjectRel, ManyToOneRel
from strawberry import UNSET
from strawberry.auto import StrawberryAuto
from strawberry.scalars import JSON

from .. import filters


@strawberry.type
class DjangoFileType:
    name: str
    path: str
    size: int
    url: str


@strawberry.type
class DjangoImageType(DjangoFileType):
    width: int
    height: int


@strawberry.type
class DjangoModelType:
    pk: strawberry.ID


@strawberry.input
class OneToOneInput:
    set: Optional[strawberry.ID]


@strawberry.input
class OneToManyInput:
    set: Optional[strawberry.ID]


@strawberry.input
class ManyToOneInput:
    add: Optional[List[strawberry.ID]] = UNSET
    remove: Optional[List[strawberry.ID]] = UNSET
    set: Optional[List[strawberry.ID]] = UNSET


@strawberry.input
class ManyToManyInput:
    add: Optional[List[strawberry.ID]] = UNSET
    remove: Optional[List[strawberry.ID]] = UNSET
    set: Optional[List[strawberry.ID]] = UNSET


field_type_map = {
    fields.AutoField: strawberry.ID,
    fields.BigAutoField: strawberry.ID,
    fields.BigIntegerField: int,
    fields.BooleanField: bool,
    fields.CharField: str,
    fields.DateField: datetime.date,
    fields.DateTimeField: datetime.datetime,
    fields.DecimalField: decimal.Decimal,
    fields.EmailField: str,
    fields.files.FileField: DjangoFileType,
    fields.FilePathField: str,
    fields.FloatField: float,
    fields.files.ImageField: DjangoImageType,
    fields.GenericIPAddressField: str,
    fields.IntegerField: int,
    fields.NullBooleanField: Optional[bool],
    fields.PositiveIntegerField: int,
    fields.PositiveSmallIntegerField: int,
    fields.SlugField: str,
    fields.SmallAutoField: strawberry.ID,
    fields.SmallIntegerField: int,
    fields.TextField: str,
    fields.TimeField: datetime.time,
    fields.URLField: str,
    fields.UUIDField: uuid.UUID,
    fields.related.ForeignKey: DjangoModelType,
    fields.reverse_related.ManyToOneRel: List[DjangoModelType],
    fields.related.OneToOneField: DjangoModelType,
    fields.reverse_related.OneToOneRel: DjangoModelType,
    fields.related.ManyToManyField: List[DjangoModelType],
    fields.reverse_related.ManyToManyRel: List[DjangoModelType],
}

if django.VERSION >= (3, 1):
    field_type_map.update(
        {
            fields.json.JSONField: JSON,
            fields.PositiveBigIntegerField: int,
        }
    )

input_field_type_map = {
    fields.files.FileField: NotImplemented,
    fields.files.ImageField: NotImplemented,
    fields.related.ForeignKey: OneToManyInput,
    fields.reverse_related.ManyToOneRel: ManyToOneInput,
    fields.related.OneToOneField: OneToOneInput,
    fields.reverse_related.OneToOneRel: OneToOneInput,
    fields.related.ManyToManyField: ManyToManyInput,
    fields.reverse_related.ManyToManyRel: ManyToManyInput,
}


def resolve_model_field_type(model_field, django_type):
    model_field_type = type(model_field)
    field_type = None
    if django_type.is_filter and model_field.is_relation:
        field_type = filters.DjangoModelFilterInput
    elif django_type.is_input:
        field_type = input_field_type_map.get(model_field_type, None)
    if field_type is None:
        field_type = field_type_map[model_field_type]
    if field_type is NotImplemented:
        raise NotImplementedError(
            f"GraphQL type for model field '{model_field}' has not been implemented"
        )
    if django_type.is_filter == "lookups":
        # TODO: could this be moved into filters.py
        if not model_field.is_relation and field_type is not bool:
            field_type = filters.FilterLookup[field_type]
    return field_type


def resolve_model_field_name(model_field, is_input=False, is_filter=False):
    if isinstance(model_field, (ForeignObjectRel, ManyToOneRel)):
        return model_field.get_accessor_name()
    if is_input and not is_filter:
        return model_field.attname
    else:
        return model_field.name


def get_model_field(model, field_name):
    try:
        return model._meta.get_field(field_name)
    except django.core.exceptions.FieldDoesNotExist as e:
        model_field_names = []

        # we need to iterate through all the fields because reverse relation
        # fields cannot be accessed by get_field method
        for field in model._meta.get_fields():
            model_field_name = resolve_model_field_name(field)
            if field_name == model_field_name:
                return field
            model_field_names.append(model_field_name)

        e.args = (
            "{}, did you mean {}?".format(
                e.args[0], ", ".join([f"'{n}'" for n in model_field_names])
            ),
        )
        raise e


def is_auto(type_):
    return isinstance(type_, StrawberryAuto)


def is_optional(model_field, is_input, partial):
    if partial:
        return True
    if not model_field:
        return False
    if is_input:
        if isinstance(model_field, fields.AutoField):
            return True
        if isinstance(model_field, fields.reverse_related.OneToOneRel):
            return model_field.null
        if model_field.many_to_many or model_field.one_to_many:
            return True
        has_default = model_field.default is not fields.NOT_PROVIDED
        if model_field.blank or has_default:
            return True
    if not isinstance(
        model_field,
        (fields.reverse_related.ManyToManyRel, fields.reverse_related.ManyToOneRel),
    ) or isinstance(model_field, fields.reverse_related.OneToOneRel):
        # OneToOneRel is the subclass of ManyToOneRel, so additional check is needed
        return model_field.null
    return False
