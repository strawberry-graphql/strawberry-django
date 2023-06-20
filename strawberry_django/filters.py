from __future__ import annotations

import functools
import inspect
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    List,
    Mapping,
    Sequence,
    TypeVar,
    cast,
)

import strawberry
from django.db.models.sql.query import get_field_names_from_opts  # type: ignore
from strawberry import UNSET
from strawberry.field import StrawberryField, field
from strawberry.unset import UnsetType
from typing_extensions import Self, dataclass_transform

from .arguments import argument
from .fields.base import StrawberryDjangoFieldBase
from .utils import (
    WithStrawberryDjangoObjectDefinition,
    WithStrawberryObjectDefinition,
    fields,
    is_django_type,
    is_strawberry_type,
    unwrap_type,
)

if TYPE_CHECKING:
    from types import FunctionType

    from django.db import models
    from django.db.models import QuerySet
    from strawberry.arguments import StrawberryArgument
    from strawberry.type import StrawberryType
    from strawberry.types import Info

T = TypeVar("T")
_QS = TypeVar("_QS", bound="QuerySet")


@strawberry.input
class DjangoModelFilterInput:
    pk: strawberry.ID


@strawberry.input
class FilterLookup(Generic[T]):
    exact: T | None = UNSET
    i_exact: T | None = UNSET
    contains: T | None = UNSET
    i_contains: T | None = UNSET
    in_list: List[T] | None = UNSET  # noqa: UP006
    gt: T | None = UNSET
    gte: T | None = UNSET
    lt: T | None = UNSET
    lte: T | None = UNSET
    starts_with: T | None = UNSET
    i_starts_with: T | None = UNSET
    ends_with: T | None = UNSET
    i_ends_with: T | None = UNSET
    range: List[T] | None = UNSET  # noqa: A003,UP006
    is_null: bool | None = UNSET
    regex: str | None = UNSET
    i_regex: str | None = UNSET


lookup_name_conversion_map = {
    "i_exact": "iexact",
    "i_contains": "icontains",
    "in_list": "in",
    "starts_with": "startswith",
    "i_starts_with": "istartswith",
    "ends_with": "endswith",
    "i_ends_with": "iendswith",
    "is_null": "isnull",
    "i_regex": "iregex",
}


def build_filter_kwargs(
    filters: WithStrawberryObjectDefinition,
) -> tuple[dict[str, Any], list[Callable]]:
    filter_kwargs = {}
    filter_methods = []
    django_model = filters._django_type.model if is_django_type(filters) else None

    for f in fields(filters):
        field_name = f.name
        field_value = getattr(filters, field_name)

        # Unset means we are not filtering this. None is still acceptable
        if field_value is UNSET:
            continue

        if isinstance(field_value, Enum):
            field_value = field_value.value

        field_name = lookup_name_conversion_map.get(field_name, field_name)
        filter_method = getattr(filters, f"filter_{field_name}", None)
        if filter_method:
            filter_methods.append(filter_method)
            continue

        if django_model and field_name not in get_field_names_from_opts(
            django_model._meta,
        ):
            continue

        if is_strawberry_type(field_value):
            subfield_filter_kwargs, subfield_filter_methods = build_filter_kwargs(
                field_value,
            )
            for subfield_name, subfield_value in subfield_filter_kwargs.items():
                if isinstance(subfield_value, Enum):
                    subfield_value = subfield_value.value  # noqa: PLW2901
                filter_kwargs[f"{field_name}__{subfield_name}"] = subfield_value

            filter_methods.extend(subfield_filter_methods)
        else:
            filter_kwargs[field_name] = field_value

    return filter_kwargs, filter_methods


@functools.lru_cache(maxsize=256)
def function_allow_passing_info(filter_method: FunctionType) -> bool:
    argspec = inspect.getfullargspec(filter_method)

    return "info" in getattr(argspec, "args", []) or "info" in getattr(
        argspec,
        "kwargs",
        [],
    )


def apply(
    filters: object | None,
    queryset: _QS,
    info: Info | None = None,
    pk: Any | None = None,
) -> _QS:
    if pk not in (None, strawberry.UNSET):
        queryset = queryset.filter(pk=pk)

    if filters in (None, strawberry.UNSET) or not is_django_type(filters):
        return queryset

    # Custom filter function in the filters object
    filter_method = getattr(filters, "filter", None)
    if filter_method:
        kwargs = {}
        if function_allow_passing_info(
            # Pass the original __func__ which is always the same
            getattr(filter_method, "__func__", filter_method),
        ):
            kwargs["info"] = info

        return filter_method(queryset=queryset, **kwargs)

    filter_kwargs, filter_methods = build_filter_kwargs(filters)
    queryset = queryset.filter(**filter_kwargs)
    for filter_method in filter_methods:
        kwargs = {}
        if function_allow_passing_info(
            # Pass the original __func__ which is always the same
            getattr(filter_method, "__func__", filter_method),
        ):
            kwargs["info"] = info

        queryset = filter_method(queryset=queryset, **kwargs)

    return queryset


class StrawberryDjangoFieldFilters(StrawberryDjangoFieldBase):
    def __init__(self, filters: type | UnsetType | None = UNSET, **kwargs):
        if filters and not is_strawberry_type(filters):
            raise TypeError("filters needs to be a strawberry type")

        self.filters = filters
        super().__init__(**kwargs)

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None:
            filters = self.get_filters()
            origin = cast(WithStrawberryObjectDefinition, self.origin)
            if (
                self.django_model
                and not self.is_list
                and origin._type_definition.name == "Query"
            ):
                arguments.append(argument("pk", strawberry.ID))
            elif filters is not None and self.is_list:
                arguments.append(argument("filters", filters, is_optional=True))

        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldFilters, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def copy_with(
        self,
        type_var_map: Mapping[TypeVar, StrawberryType | type],
    ) -> Self:
        new_field = super().copy_with(type_var_map)
        new_field.filters = self.filters
        return new_field

    def get_filters(self) -> type[WithStrawberryObjectDefinition] | None:
        filters = self.filters
        if filters is None:
            return None

        if isinstance(filters, UnsetType):
            type_ = unwrap_type(self.type)
            filters = type_._django_type.filters if is_django_type(type_) else None

        return filters

    def apply_filters(
        self,
        queryset: _QS,
        filters: WithStrawberryDjangoObjectDefinition | None,
        pk: Any | None,
        info: Info,
    ) -> _QS:
        return apply(filters, queryset, info, pk)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        filters: WithStrawberryDjangoObjectDefinition | None = None,
        pk: Any | None = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_filters(queryset, filters, pk, info)


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        field,
    ),
)
def filter(  # noqa: A001
    model: type[models.Model],
    *,
    name: str | None = None,
    description: str | None = None,
    directives: Sequence[object] | None = (),
    lookups: bool = False,
) -> Callable[[T], T]:
    from .type import input

    return input(
        model,
        name=name,
        description=description,
        directives=directives,
        is_filter="lookups" if lookups else True,
        partial=True,
    )
