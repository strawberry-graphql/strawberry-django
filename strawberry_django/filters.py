import strawberry
from typing import Generic, List, Optional, TypeVar, Union
from strawberry.field import StrawberryField
from strawberry.arguments import UNSET, is_unset, StrawberryArgument
from typing import List

from . import utils
from .arguments import argument
from .fields.types import is_auto

# for backward compatibility
from .legacy.filters import get_field_type, set_field_type

T= TypeVar("T")

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
    range: Optional[List[T]] = UNSET
    is_null: Optional[bool] = UNSET
    regex: Optional[str] = UNSET
    i_regex: Optional[str] = UNSET

lookup_name_conversion_map = {
    'i_exact': 'iexact',
    'i_contains': 'icontains',
    'in_list': 'in',
    'starts_with': 'startswith',
    'i_starts_with': 'istartswith',
    'ends_with': 'endswith',
    'i_ends_with': 'iendswith',
    'is_null': 'isnull',
    'i_regex': 'iregex',
}


def filter(model, *, name=None, lookups=False):
    try:
        import django_filters
    except ModuleNotFoundError:
        pass
    else:
        filterset_class = model
        if isinstance(filterset_class, django_filters.filterset.FilterSetMetaclass):
            utils.deprecated("support for 'django-filters' is deprecated and"
                " will removed in v0.3", stacklevel=2)
            from .legacy.filters import filter as filters_filter
            return filters_filter(filterset_class, name)

    def wrapper(cls):
        is_filter = lookups and 'lookups' or True
        from .type import process_type
        type_ = process_type(cls, model, is_input=True, partial=True, is_filter=is_filter)
        return type_
    return wrapper

def filter_deprecated(model, *, name=None, lookups=False):
    utils.deprecated("'strawberry_django.filter' is deprecated,"
        " use 'strawberry_django.filters.filter' instead", stacklevel=2)
    return filter(model, name=name, lookups=lookups)

def build_filter_kwargs(filters):
    filter_kwargs = {}
    filter_methods = []
    django_model = utils.get_django_model(filters)
    for field in utils.fields(filters):
        field_name = field.name
        field_value = getattr(filters, field_name)

        if is_unset(field_value):
            continue

        filter_method = getattr(filters, f'filter_{field_name}', None)
        if filter_method:
            filter_methods.append(filter_method)
            continue

        if django_model:
            if field_name not in django_model._meta._forward_fields_map:
                continue

        if field_name in lookup_name_conversion_map:
            field_name = lookup_name_conversion_map[field_name]
        if utils.is_strawberry_type(field_value):
            subfield_filter_kwargs, subfield_filter_methods = \
                build_filter_kwargs(field_value)
            for subfield_name, subfield_value in subfield_filter_kwargs.items():
                filter_kwargs[f'{field_name}__{subfield_name}'] = subfield_value
            filter_methods.extend(subfield_filter_methods)
        else:
            filter_kwargs[field_name] = field_value

    return filter_kwargs, filter_methods


def apply(filters, queryset, pk=UNSET):
    if not is_unset(pk):
        queryset = queryset.filter(pk=pk)
    if is_unset(filters) or filters is None:
        return queryset

    if hasattr(filters, 'filterset_class'):
        utils.deprecated("support for 'django-filters' is deprecated and"
            " will removed in v0.3", stacklevel=2)
        from .legacy.filters import apply as filters_apply
        return filters_apply(filters, queryset)

    filter_method = getattr(filters, 'filter', None)
    if filter_method:
        return filter_method(queryset)

    filter_kwargs, filter_methods = build_filter_kwargs(filters)
    queryset = queryset.filter(**filter_kwargs)
    for filter_method in filter_methods:
        queryset = filter_method(queryset=queryset)
    return queryset


class StrawberryDjangoFieldFilters:
    def __init__(self, filters=UNSET, **kwargs):
        self.filters = filters
        super().__init__(**kwargs)

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if not self.base_resolver:
            filters = self.get_filters()
            if self.django_model and not self.is_list:
                if self.is_relation is False:
                    arguments.append(
                        argument('pk', strawberry.ID)
                    )
            elif filters and not is_unset(filters):
                arguments.append(
                    argument('filters', filters)
                )
        return super().arguments + arguments

    def get_filters(self):
        if not is_unset(self.filters):
            return self.filters
        type_ = self.type or self.child.type
        if utils.is_django_type(type_):
            return type_._django_type.filters
        return None

    def get_queryset(self, queryset, info, pk=UNSET, filters=UNSET, **kwargs):
        queryset = apply(filters, queryset, pk)
        return super().get_queryset(queryset, info, **kwargs)
