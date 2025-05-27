from __future__ import annotations

import functools
import inspect
import warnings
from enum import Enum
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    cast,
)

import strawberry
from django.db.models import Q, QuerySet
from strawberry import UNSET, relay
from strawberry.tools import create_type
from strawberry.types import has_object_definition
from strawberry.types.base import WithStrawberryObjectDefinition
from strawberry.types.field import StrawberryField, field
from strawberry.types.unset import UnsetType
from typing_extensions import Self, assert_never, dataclass_transform, deprecated

from strawberry_django.fields.filter_order import (
    RESOLVE_VALUE_META,
    WITH_NONE_META,
    FilterOrderField,
    FilterOrderFieldResolver,
)
from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    has_django_definition,
)

from .arguments import argument
from .fields.base import StrawberryDjangoFieldBase
from .settings import strawberry_django_settings

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import FunctionType

    from django.db.models import Model
    from strawberry.types import Info
    from strawberry.types.arguments import StrawberryArgument


T = TypeVar("T")
_T = TypeVar("_T", bound=type)
_QS = TypeVar("_QS", bound="QuerySet")

FILTERS_ARG = "filters"


_DjangoModelFilterInput: Any = None


def get_django_model_filter_input_type():
    global _DjangoModelFilterInput  # noqa: PLW0603

    if _DjangoModelFilterInput is None:
        settings = strawberry_django_settings()

        def _get_id(root) -> str:
            return root.pk

        id_field_name = settings["DEFAULT_PK_FIELD_NAME"]
        id_field = field(
            name=id_field_name, graphql_type=strawberry.ID, resolver=_get_id
        )

        _DjangoModelFilterInput = create_type(
            "DjangoModelFilterInput",
            [id_field],  # type: ignore
            is_input=True,
        )

    return _DjangoModelFilterInput


@strawberry.input
class FilterLookup(Generic[T]):
    exact: T | None = UNSET
    i_exact: T | None = UNSET
    contains: T | None = UNSET
    i_contains: T | None = UNSET
    in_list: list[T] | None = UNSET
    gt: T | None = UNSET
    gte: T | None = UNSET
    lt: T | None = UNSET
    lte: T | None = UNSET
    starts_with: T | None = UNSET
    i_starts_with: T | None = UNSET
    ends_with: T | None = UNSET
    i_ends_with: T | None = UNSET
    range: list[T] | None = UNSET
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


def resolve_value(value: Any) -> Any:
    if isinstance(value, list):
        return [resolve_value(v) for v in value]

    if isinstance(value, relay.GlobalID):
        return value.node_id

    if isinstance(value, Enum):
        return value.value

    return value


@functools.lru_cache(maxsize=256)
def _function_allow_passing_info(filter_method: FunctionType) -> bool:
    argspec = inspect.getfullargspec(filter_method)

    return "info" in getattr(argspec, "args", []) or "info" in getattr(
        argspec,
        "kwargs",
        [],
    )


def _process_deprecated_filter(
    filter_method: FunctionType, info: Info | None, queryset: _QS
) -> _QS:
    kwargs = {}
    if _function_allow_passing_info(
        # Pass the original __func__ which is always the same
        getattr(filter_method, "__func__", filter_method),
    ):
        kwargs["info"] = info

    return filter_method(queryset=queryset, **kwargs)


def process_filters(
    filters: WithStrawberryObjectDefinition,
    queryset: _QS,
    info: Info | None,
    prefix: str = "",
    skip_object_filter_method: bool = False,
) -> tuple[_QS, Q]:
    using_old_filters = strawberry_django_settings()["USE_DEPRECATED_FILTERS"]

    q = Q()

    if not skip_object_filter_method and (
        filter_method := getattr(filters, "filter", None)
    ):
        # Dedicated function for object
        if isinstance(filter_method, FilterOrderFieldResolver):
            return filter_method(filters, info, queryset=queryset, prefix=prefix)
        if using_old_filters:
            return _process_deprecated_filter(filter_method, info, queryset), q

    # This loop relies on the filter field order that is not quaranteed for GQL input objects:
    #   "filter" has to be first since it overrides filtering for entire object
    #   DISTINCT has to be last and OR has to be after because it must be
    #       applied agains all other since default connector is AND
    for f in sorted(
        filters.__strawberry_definition__.fields,
        key=lambda x: len(x.name) if x.name in {"OR", "DISTINCT"} else 0,
    ):
        field_value = getattr(filters, f.name)
        # None is still acceptable for v1 (backwards compatibility) and filters that support it via metadata
        if field_value is UNSET or (
            field_value is None
            and not f.metadata.get(WITH_NONE_META, using_old_filters)
        ):
            continue

        should_resolve = f.metadata.get(RESOLVE_VALUE_META, UNSET)

        field_name = lookup_name_conversion_map.get(f.name, f.name)
        if field_name == "DISTINCT":
            if field_value:
                queryset = queryset.distinct()
        elif field_name in ("AND", "OR", "NOT"):  # noqa: PLR6201
            assert has_object_definition(field_value)

            queryset, sub_q = process_filters(
                cast("WithStrawberryObjectDefinition", field_value),
                queryset,
                info,
                prefix,
            )
            if field_name == "AND":
                q &= sub_q
            elif field_name == "OR":
                q |= sub_q
            elif field_name == "NOT":
                q &= ~sub_q
            else:
                assert_never(field_name)
        elif isinstance(f, FilterOrderField) and f.base_resolver:
            res = f.base_resolver(
                filters,
                info,
                value=(resolve_value(field_value) if should_resolve else field_value),
                queryset=queryset,
                prefix=prefix,
            )
            if isinstance(res, tuple):
                queryset, sub_q = res
            else:
                sub_q = res

            q &= sub_q
        elif using_old_filters and (
            filter_method := getattr(filters, f"filter_{field_name}", None)
        ):
            queryset = _process_deprecated_filter(filter_method, info, queryset)
        elif has_object_definition(field_value):
            queryset, sub_q = process_filters(
                cast("WithStrawberryObjectDefinition", field_value),
                queryset,
                info,
                f"{prefix}{field_name}__",
            )
            q &= sub_q
        else:
            q &= Q(**{
                f"{prefix}{field_name}": (
                    resolve_value(field_value)
                    if should_resolve or should_resolve is UNSET
                    else field_value
                )
            })

    return queryset, q


def apply(
    filters: object | None,
    queryset: _QS,
    info: Info | None = None,
    pk: Any | None = None,
) -> _QS:
    if pk not in (None, strawberry.UNSET):  # noqa: PLR6201
        settings = strawberry_django_settings()
        pk_field_name = settings["DEFAULT_PK_FIELD_NAME"]
        queryset = queryset.filter(**{pk_field_name: pk})

    if filters in (None, strawberry.UNSET) or not has_django_definition(filters):  # noqa: PLR6201
        return queryset

    queryset, q = process_filters(
        cast("WithStrawberryObjectDefinition", filters), queryset, info
    )
    if q:
        queryset = queryset.filter(q)
    return queryset


class StrawberryDjangoFieldFilters(StrawberryDjangoFieldBase):
    def __init__(self, filters: type | UnsetType | None = UNSET, **kwargs):
        if filters and not has_object_definition(filters):
            raise TypeError("filters needs to be a strawberry type")

        self.filters = filters
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.filters = self.filters
        return new_field

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and not self.is_model_property:
            filters = self.get_filters()
            origin = cast("WithStrawberryObjectDefinition", self.origin)
            is_root_query = origin.__strawberry_definition__.name == "Query"

            if (
                self.django_model
                and is_root_query
                and isinstance(self.django_type, relay.Node)
            ):
                arguments.append(
                    (
                        argument("ids", list[relay.GlobalID])
                        if self.is_list
                        else argument("id", relay.GlobalID)
                    ),
                )
            if (
                self.django_model
                and is_root_query
                and not self.is_list
                and not self.is_connection
                and not self.is_paginated
            ):
                settings = strawberry_django_settings()
                arguments.append(
                    argument(settings["DEFAULT_PK_FIELD_NAME"], strawberry.ID)
                )
            elif filters is not None and self.is_list:
                arguments.append(argument(FILTERS_ARG, filters, is_optional=True))

        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldFilters, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_filters(self) -> type[WithStrawberryObjectDefinition] | None:
        filters = self.filters
        if filters is None:
            return None

        if isinstance(filters, UnsetType):
            django_type = self.django_type
            filters = (
                django_type.__strawberry_django_definition__.filters
                if django_type is not None
                else None
            )

        return filters if filters is not UNSET else None

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        *,
        filters: WithStrawberryDjangoObjectDefinition | None = None,
        **kwargs,
    ) -> _QS:
        settings = strawberry_django_settings()
        pk = kwargs.get(settings["DEFAULT_PK_FIELD_NAME"], None)
        queryset = super().get_queryset(queryset, info, **kwargs)
        return apply(filters, queryset, info, pk)


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        field,
    ),
)
def filter_type(
    model: type[Model],
    *,
    name: str | None = None,
    description: str | None = None,
    directives: Sequence[object] | None = (),
    lookups: bool = False,
) -> Callable[[_T], _T]:
    from .type import input  # noqa: A004

    return input(
        model,
        name=name,
        description=description,
        directives=directives,
        is_filter="lookups" if lookups else True,
        partial=True,
    )


if TYPE_CHECKING:
    filter = deprecated("`filter` is deprecated, use `filter_type` instead.")(  # noqa: A001
        filter_type
    )


def __getattr__(name: str) -> Any:
    if name == "filter":
        warnings.warn(
            "`filter` is deprecated, use `filter_type` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return filter_type
    raise AttributeError(f"module {__name__} has no attribute {name}")
