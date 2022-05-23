import asyncio
import dataclasses
import sys
import warnings

from django.db import models
from strawberry.annotation import StrawberryAnnotation
from strawberry.field import StrawberryField
from strawberry.type import StrawberryContainer


__all__ = ["deprecated"]


def is_async() -> bool:
    # django uses the same method to detect async operation
    # https://github.com/django/django/blob/bb076476cf560b988f8d80dbbc4a3c85df54b1b9/django/utils/asyncio.py
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    else:
        return True


def deprecated(msg, stacklevel=1):
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)


def is_strawberry_type(obj):
    return hasattr(obj, "_type_definition")


def is_strawberry_field(obj):
    return isinstance(obj, StrawberryField)


def is_strawberry_django_field(obj):
    from strawberry_django.fields.field import StrawberryDjangoField

    return isinstance(obj, StrawberryDjangoField)


def is_django_type(obj):
    return hasattr(obj, "_django_type")


def is_django_model(obj):
    return isinstance(obj, models.base.ModelBase)


def is_field(obj):
    return isinstance(obj, dataclasses.Field)


def is_django_field(obj):
    from .fields.field import DjangoField

    return isinstance(obj, DjangoField)


def fields(obj):
    return obj._type_definition.fields


def is_auto(obj):
    from .fields.types import is_auto

    return is_auto(obj)


def get_django_model(type_):
    if not is_django_type(type_):
        return
    return type_._django_type.model


def is_similar_django_type(a, b):
    if not a or not b:
        return False
    if a.is_input != b.is_input:
        return False
    if a.is_filter != b.is_filter:
        return False
    return True


def get_annotations(cls):
    annotations = {}
    namespace = sys.modules[cls.__module__].__dict__
    for c in reversed(cls.__mro__):
        if "__annotations__" in c.__dict__:
            annotations.update(
                {
                    k: StrawberryAnnotation(v, namespace=namespace)
                    for k, v in c.__annotations__.items()
                }
            )
    return annotations


def unwrap_type(type_):
    while isinstance(type_, StrawberryContainer):
        type_ = type_.of_type

    return type_
