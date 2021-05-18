import dataclasses
import strawberry
from strawberry.arguments import is_unset, UNSET
from strawberry.field import StrawberryField
from django.db import models
import asyncio
import warnings


def is_async():
    # django uses the same method to detect async operation
    # https://github.com/django/django/blob/76c0b32f826469320c59709d31e2f2126dd7c505/django/utils/asyncio.py
    try:
        event_loop = asyncio.get_event_loop()
    except RuntimeError:
        pass
    else:
        if event_loop.is_running():
            return True
    return False


def deprecated(msg, stacklevel=1):
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)

def is_strawberry_type(obj):
    return hasattr(obj, '_type_definition')

def is_strawberry_field(obj):
    return isinstance(obj, StrawberryField)

def is_strawberry_django_field(obj):
    from strawberry_django.fields.field import StrawberryDjangoField
    return isinstance(obj, StrawberryDjangoField)

def is_django_type(obj):
    return hasattr(obj, '_django_type')

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
    for c in reversed(cls.__mro__):
        if '__annotations__' in c.__dict__:
            annotations.update(c.__annotations__)
    return annotations
