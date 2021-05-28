import dataclasses
import django
import strawberry
from django.db import models
from strawberry.arguments import UNSET, is_unset
from typing import Any, Optional

from .fields.field import StrawberryDjangoField
from .fields.types import (
    is_optional,
    get_model_field, resolve_model_field_type, resolve_model_field_name,
)
from . import utils

_type = type

def get_type_attr(type_, field_name):
    attr = getattr(type_, field_name, UNSET)
    if utils.is_unset(attr):
        attr = getattr(type_, '__dataclass_fields__', {}).get(field_name, UNSET)
    return attr

def get_field(django_type, field_name, field_annotation=None):
    attr = get_type_attr(django_type.origin, field_name)

    if utils.is_field(attr):
        field = StrawberryDjangoField.from_field(attr, django_type)
    else:
        field = StrawberryDjangoField(
            default=attr,
            type_=field_annotation,
        )

    field.python_name = field_name
    if field_name in django_type.origin.__dict__.get('__annotations__', {}):
        # store origin django type for futher usage
        field.origin_django_type = django_type

    if field_annotation:
        # annotation of field is used as a class type
        field.type = field_annotation
        field.is_auto = utils.is_auto(field_annotation)

    try:
        # resolve the django_name and check if it is relation field. django_name
        # is used to access the field data in resolvers
        django_name = field.django_name or field_name
        model_field = get_model_field(django_type.model, django_name)
        field.django_name = resolve_model_field_name(model_field,
                django_type.is_input, django_type.is_filter)
        field.is_relation = model_field.is_relation
    except django.core.exceptions.FieldDoesNotExist:
        if field.django_name or field.is_auto:
            raise # field should exist, reraise catched exception
        model_field = None

    if field.is_relation:
        # change relation field type to auto if field is inherited from another
        # type. for example if field is inherited from output type but we are
        # configuring field for input type
        if not utils.is_similar_django_type(django_type, field.origin_django_type):
            field.is_auto = True

    if field.is_auto:
        # resolve type of auto field
        field.type = resolve_model_field_type(model_field, django_type)

    if is_optional(model_field, django_type.is_input, django_type.is_partial):
        field.type = Optional[field.type]
    
    if django_type.is_input:
        if field.default is dataclasses.MISSING:
            # strawberry converts UNSET value to MISSING, let's set
            # it back to UNSET. this is important especially for partial
            # input types
            #TODO: could strawberry support UNSET default value?
            field.default_value = UNSET
            field.default = UNSET

    return field


def get_fields(django_type):
    annotations = utils.get_annotations(django_type.origin)
    fields = {}

    # collect all annotated fields
    for field_name, field_annotation in annotations.items():
        field = get_field(django_type, field_name, field_annotation)
        fields[field_name] = field

    # collect non-annotated strawberry fields
    for field_name in dir(django_type.origin):
        if field_name in fields:
            continue
        attr = getattr(django_type.origin, field_name)
        if not utils.is_strawberry_field(attr):
            continue
        field = get_field(django_type, field_name)
        fields[field_name] = field

    return list(fields.values())



@dataclasses.dataclass
class StrawberryDjangoType:
    origin: Any
    model: Any
    is_input: bool
    is_partial: bool
    is_filter: bool
    filters: Any
    order: Any
    pagination: Any

def process_type(cls, model, *, filters=UNSET, pagination=UNSET, order=UNSET, **kwargs):
    original_annotations = cls.__dict__.get('__annotations__', {})

    django_type = StrawberryDjangoType(
        origin=cls,
        model=model,
        is_input=kwargs.get('is_input', False),
        is_partial=kwargs.pop('partial', False),
        is_filter=kwargs.pop('is_filter', False),
        filters=filters,
        order=order,
        pagination=pagination,
    )

    fields = get_fields(django_type)

    # update annotations and fields
    cls.__annotations__ = cls_annotations = {}
    for field in fields:
        cls_annotations[field.name] = field.type
        setattr(cls, field.name, field)

    strawberry.type(cls, **kwargs)

    # restore original annotations for further use
    cls.__annotations__ = original_annotations
    cls._django_type = django_type

    return cls
    

def type(model, *, filters=UNSET, **kwargs):
    if 'fields' in kwargs or 'types' in kwargs:
        from .legacy.type import type as type_legacy
        return type_legacy(model, **kwargs)

    def wrapper(cls):
        return process_type(cls, model, filters=filters, **kwargs)

    return wrapper


def input(model, *, partial=False, **kwargs):
    return type(model, partial=partial, is_input=True, **kwargs)

def mutation(model, **kwargs):
    return type(model, **kwargs)
