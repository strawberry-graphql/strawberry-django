import dataclasses
from typing import Any, Optional, TypeVar

import django
import strawberry
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation

from . import utils
from .fields.field import StrawberryDjangoField, StrawberryDjangoFieldBase
from .fields.types import (
    get_model_field,
    is_optional,
    resolve_model_field_name,
    resolve_model_field_type,
)


_type = type

StrawberryDjangoFieldType = TypeVar(
    "StrawberryDjangoFieldType", bound=StrawberryDjangoFieldBase
)


def get_type_attr(type_, field_name):
    attr = getattr(type_, field_name, UNSET)
    if attr is UNSET:
        attr = getattr(type_, "__dataclass_fields__", {}).get(field_name, UNSET)
    return attr


def get_field(django_type, field_name, field_annotation=None):
    if field_annotation is None:
        field_annotation = StrawberryAnnotation(None)
    attr = get_type_attr(django_type.origin, field_name)

    if utils.is_field(attr):
        field = django_type.field_cls.from_field(attr, django_type)
    else:
        field = django_type.field_cls(
            default=attr,
            type_annotation=field_annotation,
        )

    field.python_name = field_name
    if field_name in django_type.origin.__dict__.get("__annotations__", {}):
        # store origin django type for further usage
        field.origin_django_type = django_type

    if field_annotation:
        # annotation of field is used as a class type
        field.type_annotation = field_annotation
        field.is_auto = utils.is_auto(field_annotation)

    try:
        # resolve the django_name and check if it is relation field. django_name
        # is used to access the field data in resolvers
        django_name = field.django_name or field_name
        model_field = get_model_field(django_type.model, django_name)
        field.django_name = resolve_model_field_name(
            model_field, django_type.is_input, django_type.is_filter
        )
        field.is_relation = model_field.is_relation
    except django.core.exceptions.FieldDoesNotExist:
        if field.django_name or field.is_auto:
            raise  # field should exist, reraise caught exception
        model_field = None

    if field.is_relation:
        # change relation field type to auto if field is inherited from another
        # type. for example if field is inherited from output type but we are
        # configuring field for input type
        if not utils.is_similar_django_type(django_type, field.origin_django_type):
            field.is_auto = True

    if field.is_auto:
        # resolve type of auto field
        field_type = resolve_model_field_type(model_field, django_type)
        field.type_annotation = StrawberryAnnotation(field_type)

    if is_optional(model_field, django_type.is_input, django_type.is_partial):
        field.type_annotation.annotation = Optional[field.type_annotation.annotation]

    if django_type.is_input:
        if field.default is dataclasses.MISSING:
            # strawberry converts UNSET value to MISSING, let's set
            # it back to UNSET. this is important especially for partial
            # input types
            # TODO: could strawberry support UNSET default value?
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
    field_cls: StrawberryDjangoFieldType


def process_type(
    cls,
    model,
    *,
    filters=UNSET,
    pagination=UNSET,
    order=UNSET,
    field_cls=UNSET,
    **kwargs
):
    original_annotations = cls.__dict__.get("__annotations__", {})

    if not field_cls or field_cls is UNSET:
        field_cls = StrawberryDjangoField

    django_type = StrawberryDjangoType(
        origin=cls,
        model=model,
        is_input=kwargs.get("is_input", False),
        is_partial=kwargs.pop("partial", False),
        is_filter=kwargs.pop("is_filter", False),
        filters=filters,
        order=order,
        pagination=pagination,
        field_cls=field_cls,
    )

    fields = get_fields(django_type)

    # update annotations and fields
    cls.__annotations__ = cls_annotations = {}
    for field in fields:
        annotation = (
            field.type
            if field.type_annotation is None
            else field.type_annotation.annotation
        )
        if annotation is None:
            annotation = StrawberryAnnotation(strawberry.auto)
        cls_annotations[field.name] = annotation
        setattr(cls, field.name, field)

    # Strawberry >= 0.92.0 defines `is_type_of` for types implementing
    # interfaces if the attribute has not been set yet. It allows only
    # instances of `cls` to be returned, we should allow model instances
    # too.
    if not hasattr(cls, "is_type_of"):
        cls.is_type_of = lambda obj, _info: isinstance(obj, (cls, model))

    strawberry.type(cls, **kwargs)

    # restore original annotations for further use
    cls.__annotations__ = original_annotations
    cls._django_type = django_type

    return cls


def type(model, *, filters=UNSET, **kwargs):
    def wrapper(cls):
        return process_type(cls, model, filters=filters, **kwargs)

    return wrapper


def input(model, *, partial=False, **kwargs):
    return type(model, partial=partial, is_input=True, **kwargs)


def mutation(model, **kwargs):
    return type(model, **kwargs)
