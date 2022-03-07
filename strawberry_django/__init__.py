# FIXME: We should stop exporting this in the future and auto directly from strawberry
from strawberry import auto

from . import auth, filters, mutations, ordering, types
from .fields.field import field
from .fields.types import (
    DjangoFileType,
    DjangoImageType,
    DjangoModelType,
    ManyToManyInput,
    ManyToOneInput,
    OneToManyInput,
    OneToOneInput,
    is_auto,
)
from .filters import filter_deprecated as filter
from .resolvers import django_resolver
from .type import input, mutation, type
from .utils import fields


__all__ = [
    "auth",
    "filters",
    "filter",
    "ordering",
    "types",
    "field",
    "auto",
    "is_auto",
    "DjangoFileType",
    "DjangoImageType",
    "DjangoModelType",
    "OneToOneInput",
    "OneToManyInput",
    "ManyToOneInput",
    "ManyToManyInput",
    "fields",
    "mutations",
    "django_resolver",
    "type",
    "input",
    "mutation",
]
