import functools
import inspect
from enum import Enum
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import strawberry
from django.db import models
from django.db.models.sql.query import get_field_names_from_opts  # type: ignore
from strawberry import UNSET, relay
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField, field
from strawberry.type import WithStrawberryObjectDefinition, has_object_definition
from strawberry.types import Info
from strawberry.unset import UnsetType
from typing_extensions import Self, dataclass_transform

from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    has_django_definition,
)

from .arguments import argument
from .fields.base import StrawberryDjangoFieldBase

if TYPE_CHECKING:
    from django.db.models import QuerySet

T = TypeVar("T")
_QS = TypeVar("_QS", bound="QuerySet")


@strawberry.input
class DjangoModelFilterInput:
    pk: strawberry.ID


@strawberry.input
class FilterLookup(Generic[T]):
    exact: Optional[T] = UNSET
    i_exact: Optional[T] = UNSET
    contains: Optional[T] = UNSET
    i_contains: Optional[T] = UNSET
    in_list: Optional[List[T]] = UNSET
    gt: Optional[T] = UNSET
    gte: Optional[T] = UNSET
    lt: Optional[T] = UNSET
    lte: Optional[T] = UNSET
    starts_with: Optional[T] = UNSET
    i_starts_with: Optional[T] = UNSET
    ends_with: Optional[T] = UNSET
    i_ends_with: Optional[T] = UNSET
    range: Optional[List[T]] = UNSET  # noqa: A003
    is_null: Optional[bool] = UNSET
    regex: Optional[str] = UNSET
    i_regex: Optional[str] = UNSET


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


def _resolve_global_id(value: Any):
    if isinstance(value, list):
        return [_resolve_global_id(v) for v in value]
    if isinstance(value, relay.GlobalID):
        return value.node_id

    return value


def build_filter_kwargs(
    filters: WithStrawberryObjectDefinition,
) -> Tuple[Dict[str, Any], List[Callable]]:
    filter_kwargs = {}
    filter_methods = []
    django_model = (
        filters.__strawberry_django_definition__.model
        if has_django_definition(filters)
        else None
    )

    for f in filters.__strawberry_definition__.fields:
        field_name = f.name
        field_value = _resolve_global_id(getattr(filters, field_name))

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

        if has_object_definition(field_value):
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
    filters: Optional[object],
    queryset: _QS,
    info: Optional[Info] = None,
    pk: Optional[Any] = None,
) -> _QS:
    if pk not in (None, strawberry.UNSET):
        queryset = queryset.filter(pk=pk)

    if filters in (None, strawberry.UNSET) or not has_django_definition(filters):
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
    def __init__(self, filters: Union[type, UnsetType, None] = UNSET, **kwargs):
        if filters and not has_object_definition(filters):
            raise TypeError("filters needs to be a strawberry type")

        self.filters = filters
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.filters = self.filters
        return new_field

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None:
            filters = self.get_filters()
            origin = cast(WithStrawberryObjectDefinition, self.origin)
            is_root_query = origin.__strawberry_definition__.name == "Query"

            if (
                self.django_model
                and is_root_query
                and isinstance(self.django_type, relay.Node)
            ):
                arguments.append(
                    (
                        argument("ids", List[relay.GlobalID])
                        if self.is_list
                        else argument("id", relay.GlobalID)
                    ),
                )
            if (
                self.django_model
                and is_root_query
                and not self.is_list
                and not self.is_connection
            ):
                arguments.append(argument("pk", strawberry.ID))
            elif filters is not None and self.is_list:
                arguments.append(argument("filters", filters, is_optional=True))

        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: List[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldFilters, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_filters(self) -> Optional[Type[WithStrawberryObjectDefinition]]:
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

        return filters

    def apply_filters(
        self,
        queryset: _QS,
        filters: Optional[WithStrawberryDjangoObjectDefinition],
        pk: Optional[Any],
        info: Info,
    ) -> _QS:
        return apply(filters, queryset, info, pk)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        filters: Optional[WithStrawberryDjangoObjectDefinition] = None,
        pk: Optional[Any] = None,
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
    model: Type[models.Model],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
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
