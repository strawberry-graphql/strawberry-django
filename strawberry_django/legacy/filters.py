import functools
from typing import Type, Optional, List
import strawberry
from graphql import GraphQLError
from strawberry.arguments import UNSET, is_unset


__all__ = [
    "InvalidFilterError",
    "apply",
    "filter",
    "get_field_type",
    "set_field_type",
]


class DummyDjangoFilters:
    def __getattribute__(self, attr):
        # make mocker happy
        if attr == '__enter__':
            raise AttributeError

try:
    import django_filters
except ModuleNotFoundError:
    django_filters = DummyDjangoFilters()


def assert_django_filters_installed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if isinstance(django_filters, DummyDjangoFilters):
            raise ModuleNotFoundError(
                'You need to install django-filter to use "strawberry_django.filter". '
                "See https://django-filter.readthedocs.io/"
            )
        return fn(*args, **kwargs)
    return wrapper


# TODO
#  Some projects might want to change this to eg UUID
#  We should make it configurable
#  In the meantime they can overwrite "type_map" using "set_filter_field_type"
ID_TYPE = strawberry.ID


filter_field_type_map = {
    django_filters.BooleanFilter: Optional[bool],
    django_filters.CharFilter: Optional[str],
    django_filters.ChoiceFilter: Optional[str],
    django_filters.DateFilter: Optional[str],
    django_filters.DateTimeFilter: Optional[str],
    django_filters.DurationFilter: Optional[str],
    django_filters.IsoDateTimeFilter: Optional[str],
    django_filters.ModelChoiceFilter: Optional[ID_TYPE],
    django_filters.ModelMultipleChoiceFilter: Optional[List[ID_TYPE]],
    django_filters.MultipleChoiceFilter: Optional[List[str]],
    # Use str for number fields, because it might be int, decimal or float, and casting
    # it to any of those types might cause incorrect results for the other types.
    django_filters.NumberFilter: Optional[str],
    django_filters.TimeFilter: Optional[str],
    django_filters.UUIDFilter: Optional[str],

    # Not implemented because its difficult or impossible to create input types:
    # django_filters.AllValuesFilter
    # django_filters.AllValuesMultipleFilter
    # django_filters.DateFromToRangeFilter
    # django_filters.DateRangeFilter
    # django_filters.DateTimeFromToRangeFilter
    # django_filters.IsoDateTimeFromToRangeFilter
    # django_filters.OrderingFilter
    # django_filters.RangeFilter
    # django_filters.NumericRangeFilter
    # django_filters.TimeRangeFilter
    # django_filters.LookupChoiceFilter
    # django_filters.TypedChoiceFilter
    # django_filters.TypedMultipleChoiceFilter
}


class InvalidFilterError(GraphQLError):
    pass


@assert_django_filters_installed
def get_field_type(field_type):
    if type(field_type) != type:
        raise TypeError(
            f"expected 'type', received {type(field_type)}. Maybe you forgot to call type()?"
        )
    try:
        return filter_field_type_map[field_type]
    except KeyError:
        raise TypeError(f"No type defined for field type '{field_type}'")


@assert_django_filters_installed
def set_field_type(field_type, to_type):
    if type(field_type) != type:
        raise TypeError(
            f"expected 'type', received {type(field_type)}. Maybe you forgot to call type()?"
        )
    filter_field_type_map[field_type] = to_type


@assert_django_filters_installed
def apply(filter_instance, queryset):
    if is_unset(filter_instance) or not filter_instance:
        return queryset

    data = {}
    for field_name in filter_instance.filterset_class.get_fields():
        value = getattr(filter_instance, field_name, None)
        if not is_unset(value):
            data[field_name] = value

    filterset = filter_instance.filterset_class(
        data=data,
        queryset=queryset,
    )

    if not filterset.is_valid():
        raise InvalidFilterError(filterset.errors)

    return filterset.qs


@assert_django_filters_installed
def filter(filterset_class: Type[django_filters.FilterSet], name=None):
    if not isinstance(filterset_class, django_filters.filterset.FilterSetMetaclass):
        raise TypeError(
            "strawberry_django.filter expects a class that inherits django_filters.FilterSet, received %s",
            type(filterset_class),
        )

    filters = filterset_class.get_filters()
    name = name or filterset_class.__name__
    cls = type(name, (), {"__annotations__": {}, "filterset_class": filterset_class})

    for field_name in filterset_class.get_filters().keys():
        filter_field = filters[field_name]
        field_type = get_field_type(type(filter_field))
        cls.__annotations__[field_name] = field_type
        setattr(cls, field_name, UNSET)

    return strawberry.input(cls)
