import functools
import inspect
from enum import Enum
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
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
from django.db.models import Q
from django.db.models.sql.query import get_field_names_from_opts  # type: ignore
from strawberry import UNSET, relay
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField, field
from strawberry.type import WithStrawberryObjectDefinition, has_object_definition
from strawberry.types import Info
from strawberry.unset import UnsetType
from typing_extensions import Self, assert_never, dataclass_transform

from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    has_django_definition,
)

from .arguments import argument
from .fields.base import StrawberryDjangoFieldBase

if TYPE_CHECKING:
    from django.db.models import QuerySet

T = TypeVar("T")
_T = TypeVar("_T", bound=type)
_QS = TypeVar("_QS", bound="QuerySet")

FILTERS_ARG = "filters"


@strawberry.input
class DjangoModelFilterInput:
    pk: strawberry.ID


_n_deprecation_reason = """\
The "n" prefix is deprecated and will be removed in the future, use `NOT` instead.
"""


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
    n_exact: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_i_exact: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_contains: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_i_contains: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_in_list: Optional[List[T]] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_gt: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_gte: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_lt: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_lte: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_starts_with: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_i_starts_with: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_ends_with: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_i_ends_with: Optional[T] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_range: Optional[List[T]] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_is_null: Optional[bool] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_regex: Optional[str] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )
    n_i_regex: Optional[str] = strawberry.field(
        default=UNSET,
        deprecation_reason=_n_deprecation_reason,
    )


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
    path="",
) -> Tuple[Q, List[Callable]]:
    filter_kwargs = Q()
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
        elif (
            isinstance(field_value, list)
            and len(field_value) > 0
            and isinstance(field_value[0], Enum)
        ):
            field_value = [el.value for el in field_value]

        negated = False
        if field_name.startswith("n_"):
            field_name = field_name[2:]
            negated = True

        field_name = lookup_name_conversion_map.get(field_name, field_name)
        filter_method = getattr(
            filters,
            f"filter_{'n_' if negated else ''}{field_name}",
            None,
        )
        if filter_method:
            filter_methods.append(filter_method)
            continue

        if django_model:
            if field_name in ("AND", "OR", "NOT"):  # noqa: PLR6201
                if has_object_definition(field_value):
                    (
                        subfield_filter_kwargs,
                        subfield_filter_methods,
                    ) = build_filter_kwargs(field_value, path)
                    if field_name == "AND":
                        filter_kwargs &= subfield_filter_kwargs
                    elif field_name == "OR":
                        filter_kwargs |= subfield_filter_kwargs
                    elif field_name == "NOT":
                        filter_kwargs &= ~subfield_filter_kwargs
                    else:
                        assert_never(field_name)

                    filter_methods.extend(subfield_filter_methods)
                continue

            if field_name not in get_field_names_from_opts(
                django_model._meta,
            ):
                continue

        if has_object_definition(field_value):
            subfield_filter_kwargs, subfield_filter_methods = build_filter_kwargs(
                field_value,
                f"{path}{field_name}__",
            )
            filter_kwargs &= subfield_filter_kwargs
            filter_methods.extend(subfield_filter_methods)
        else:
            filter_kwarg = Q(**{f"{path}{field_name}": field_value})
            if negated:
                filter_kwarg = ~filter_kwarg
            filter_kwargs &= filter_kwarg

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
    if pk not in (None, strawberry.UNSET):  # noqa: PLR6201
        queryset = queryset.filter(pk=pk)

    if filters in (None, strawberry.UNSET) or not has_django_definition(filters):  # noqa: PLR6201
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
    queryset = queryset.filter(filter_kwargs)
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
                arguments.append(argument(FILTERS_ARG, filters, is_optional=True))

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

        return filters if filters is not UNSET else None

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
) -> Callable[[_T], _T]:
    from .type import input

    return input(
        model,
        name=name,
        description=description,
        directives=directives,
        is_filter="lookups" if lookups else True,
        partial=True,
    )
