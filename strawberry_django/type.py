import dataclasses
from contextlib import suppress
from inspect import cleandoc
from typing import Any, Dict, Generic, Optional, Type, TypeVar

import django
import django.db.models
import strawberry
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.exceptions import PrivateStrawberryFieldError
from strawberry.field import UNRESOLVED
from strawberry.private import is_private

from . import utils
from .fields.field import StrawberryDjangoField
from .fields.types import (
    get_model_field,
    is_optional,
    resolve_model_field_name,
    resolve_model_field_type,
)
from .settings import strawberry_django_settings as django_settings

_type = type


def get_type_attr(type_, field_name: str):
    attr = getattr(type_, field_name, UNSET)
    if attr is UNSET:
        return getattr(type_, "__dataclass_fields__", {}).get(field_name, UNSET)
    return attr


def get_field(
    django_type: "StrawberryDjangoType",
    field_name: str,
    field_annotation: Optional[StrawberryAnnotation] = None,
):
    if field_annotation and is_private(field_annotation.annotation):
        raise PrivateStrawberryFieldError(field_name, django_type.origin)
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
            model_field,
            django_type.is_input,
            django_type.is_filter,
        )
        field.is_relation = model_field.is_relation

        # Use the Django field help_text if no other description is available.
        settings = django_settings()
        if not field.description and settings["FIELD_DESCRIPTION_FROM_HELP_TEXT"]:
            model_field_help_text = getattr(model_field, "help_text", "")
            field.description = str(model_field_help_text) or None
    except django.core.exceptions.FieldDoesNotExist:
        if field.django_name or field.is_auto:
            raise  # field should exist, reraise caught exception
        model_field = None

    # change relation field type to auto if field is inherited from another
    # type. for example if field is inherited from output type but we are
    # configuring field for input type
    if field.is_relation and not utils.is_similar_django_type(
        django_type,
        field.origin_django_type,
    ):
        field.is_auto = True

    # Only set the type_annotation for auto fields if they don't have a base_resolver.
    # Since strawberry 0.139 the type_annotation has a higher priority than the
    # resolver's annotation, and that would force our automatic model resolution to be
    # used instead of the resolver's type annotation.
    if field.is_auto and not field.base_resolver:
        # resolve type of auto field
        field_type = resolve_model_field_type(model_field, django_type)
        field.type_annotation = StrawberryAnnotation(field_type)

    if field.type_annotation and is_optional(
        model_field,
        django_type.is_input,
        django_type.is_partial,
    ):
        field.type_annotation.annotation = Optional[field.type_annotation.annotation]

    if django_type.is_input and field.default is dataclasses.MISSING:
        # strawberry converts UNSET value to MISSING, let's set
        # it back to UNSET. this is important especially for partial
        # input types
        # TODO: could strawberry support UNSET default value?
        field.default_value = UNSET
        field.default = UNSET

    return field


def get_fields(django_type: "StrawberryDjangoType"):
    annotations = utils.get_annotations(django_type.origin)
    fields: Dict[str, StrawberryDjangoField] = {}
    seen_fields = set()

    # collect all annotated fields
    for field_name, field_annotation in annotations.items():
        with suppress(PrivateStrawberryFieldError):
            fields[field_name] = get_field(django_type, field_name, field_annotation)
        seen_fields.add(field_name)

    # collect non-annotated strawberry fields
    for field_name in dir(django_type.origin):
        if field_name in seen_fields:
            continue
        attr = getattr(django_type.origin, field_name)
        if not utils.is_strawberry_field(attr):
            continue
        field = get_field(django_type, field_name)
        fields[field_name] = field

    return list(fields.values())


_O = TypeVar("_O", bound=type)
_M = TypeVar("_M", bound=django.db.models.Model)


@dataclasses.dataclass
class StrawberryDjangoType(Generic[_O, _M]):
    origin: _O
    model: Type[_M]
    is_input: bool
    is_partial: bool
    is_filter: bool
    filters: Any
    order: Any
    pagination: Any
    field_cls: Type[StrawberryDjangoField]


def process_type(
    cls,
    model: Type[django.db.models.Model],
    *,
    filters=UNSET,
    pagination=UNSET,
    order=UNSET,
    field_cls=UNSET,
    **kwargs,
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
        annotation = None

        if field.type_annotation and field.type_annotation.annotation:
            annotation = field.type_annotation.annotation
        elif field.base_resolver and field.base_resolver.type_annotation:
            annotation = field.base_resolver.type_annotation.annotation

        # UNRESOLVED is not a valid annotation, it is just an indication that the type
        # could not be resolved. In this case just fallback to None
        if annotation is UNRESOLVED:
            annotation = None

        # TODO: should we raise an error if annotation is None here?

        cls_annotations[field.name] = annotation
        setattr(cls, field.name, field)

    # Strawberry >= 0.92.0 defines `is_type_of` for types implementing
    # interfaces if the attribute has not been set yet. It allows only
    # instances of `cls` to be returned, we should allow model instances
    # too.
    if not hasattr(cls, "is_type_of"):
        cls.is_type_of = lambda obj, _info: isinstance(obj, (cls, model))

    # Get type description from either kwargs, or the model's docstring
    settings = django_settings()
    description = kwargs.pop("description", None)
    if not description and settings["TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING"]:
        description = cleandoc(model.__doc__) or None

    strawberry.type(cls, description=description, **kwargs)

    # restore original annotations for further use
    cls.__annotations__ = original_annotations
    cls._django_type = django_type

    return cls


# FIXME: This needs proper typing
def type(model, *, filters=UNSET, **kwargs):  # noqa: A001
    def wrapper(cls):
        return process_type(cls, model, filters=filters, **kwargs)

    return wrapper


# FIXME: This needs proper typing
def input(model, *, partial=False, **kwargs):  # noqa: A001
    return type(model, partial=partial, is_input=True, **kwargs)


# FIXME: This needs proper typing
def mutation(model, **kwargs):
    return type(model, **kwargs)
