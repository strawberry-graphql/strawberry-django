from . import auth, filters, ordering, types
from .fields.field import field
from .fields.types import (
    auto, is_auto,
    DjangoFileType, DjangoImageType, DjangoModelType,
    OneToOneInput, OneToManyInput, ManyToOneInput, ManyToManyInput,
)
from .utils import fields
from .filters import filter_deprecated as filter
from .mutations.mutations import mutations
from .resolvers import django_resolver
from .type import type, input, mutation

# deprecated functions
from .legacy.mutations.auth import AuthMutation
from .legacy.queries.fields import queries
from .legacy.registers import TypeRegister


__all__ = [
    'auth',
    'filters',
    'ordering',
    'types',
    'field',
    'auto',
    'is_auto',
    'DjangoFileType',
    'DjangoImageType',
    'DjangoModelType',
    'OneToOneInput',
    'OneToManyInput',
    'ManyToOneInput',
    'ManyToManyInput',
    'fields',
    'filter',
    'mutations',
    'type',
    'django_resolver',
    'input',
    'mutation',
    'queries',
    'AuthMutation',
    'TypeRegister',
]