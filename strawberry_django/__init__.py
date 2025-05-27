import warnings
from typing import TYPE_CHECKING, Any

from . import auth, filters, mutations, ordering, pagination, relay
from .fields.field import connection, field, node, offset_paginated
from .fields.filter_order import filter_field, order_field
from .fields.filter_types import (
    BaseFilterLookup,
    ComparisonFilterLookup,
    DateFilterLookup,
    DatetimeFilterLookup,
    FilterLookup,
    RangeLookup,
    TimeFilterLookup,
)
from .fields.types import (
    DjangoFileType,
    DjangoImageType,
    DjangoModelType,
    ListInput,
    ManyToManyInput,
    ManyToOneInput,
    NodeInput,
    NodeInputPartial,
    OneToManyInput,
    OneToOneInput,
)
from .filters import filter_type, process_filters
from .mutations.mutations import input_mutation, mutation
from .ordering import Ordering, order, order_type, process_order
from .resolvers import django_resolver
from .type import input, interface, partial, type  # noqa: A004

if TYPE_CHECKING:
    from strawberry_django.filters import filter  # noqa: A004, F401

__all__ = [
    "BaseFilterLookup",
    "ComparisonFilterLookup",
    "DateFilterLookup",
    "DatetimeFilterLookup",
    "DjangoFileType",
    "DjangoImageType",
    "DjangoModelType",
    "FilterLookup",
    "ListInput",
    "ManyToManyInput",
    "ManyToOneInput",
    "NodeInput",
    "NodeInputPartial",
    "OneToManyInput",
    "OneToOneInput",
    "Ordering",
    "RangeLookup",
    "TimeFilterLookup",
    "auth",
    "connection",
    "django_resolver",
    "field",
    "filter_field",
    "filter_type",
    "filters",
    "input",
    "input_mutation",
    "interface",
    "mutation",
    "mutations",
    "node",
    "offset_paginated",
    "order",
    "order_field",
    "order_type",
    "ordering",
    "pagination",
    "partial",
    "process_filters",
    "process_order",
    "relay",
    "type",
]


def __getattr__(name: str) -> Any:
    if name == "filter":
        warnings.warn(
            "`filter` is deprecated, use `filter_type` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return filter_type
    raise AttributeError(f"module {__name__} has no attribute {name}")
