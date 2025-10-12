import datetime
import decimal
import uuid
from typing import (
    Generic,
    TypeVar,
)

import strawberry
from django.db.models import Q
from strawberry import UNSET

from strawberry_django.filters import resolve_value

from .filter_order import filter_field

T = TypeVar("T")

_SKIP_MSG = "Filter will be skipped on `null` value"


@strawberry.input
class BaseFilterLookup(Generic[T]):
    exact: T | None = filter_field(description=f"Exact match. {_SKIP_MSG}")
    is_null: bool | None = filter_field(description=f"Assignment test. {_SKIP_MSG}")
    in_list: list[T] | None = filter_field(
        description=f"Exact match of items in a given list. {_SKIP_MSG}"
    )


@strawberry.input
class RangeLookup(Generic[T]):
    start: T | None = None
    end: T | None = None

    @filter_field
    def filter(self, queryset, prefix: str):
        return queryset, Q(**{
            prefix[:-2]: [resolve_value(self.start), resolve_value(self.end)]
        })


@strawberry.input
class ComparisonFilterLookup(BaseFilterLookup[T]):
    gt: T | None = filter_field(description=f"Greater than. {_SKIP_MSG}")
    gte: T | None = filter_field(description=f"Greater than or equal to. {_SKIP_MSG}")
    lt: T | None = filter_field(description=f"Less than. {_SKIP_MSG}")
    lte: T | None = filter_field(description=f"Less than or equal to. {_SKIP_MSG}")
    range: RangeLookup[T] | None = filter_field(
        description="Inclusive range test (between)"
    )


@strawberry.input
class FilterLookup(BaseFilterLookup[T]):
    i_exact: T | None = filter_field(
        description=f"Case-insensitive exact match. {_SKIP_MSG}"
    )
    contains: T | None = filter_field(
        description=f"Case-sensitive containment test. {_SKIP_MSG}"
    )
    i_contains: T | None = filter_field(
        description=f"Case-insensitive containment test. {_SKIP_MSG}"
    )
    starts_with: T | None = filter_field(
        description=f"Case-sensitive starts-with. {_SKIP_MSG}"
    )
    i_starts_with: T | None = filter_field(
        description=f"Case-insensitive starts-with. {_SKIP_MSG}"
    )
    ends_with: T | None = filter_field(
        description=f"Case-sensitive ends-with. {_SKIP_MSG}"
    )
    i_ends_with: T | None = filter_field(
        description=f"Case-insensitive ends-with. {_SKIP_MSG}"
    )
    regex: T | None = filter_field(
        description=f"Case-sensitive regular expression match. {_SKIP_MSG}"
    )
    i_regex: T | None = filter_field(
        description=f"Case-insensitive regular expression match. {_SKIP_MSG}"
    )


@strawberry.input
class DateFilterLookup(ComparisonFilterLookup[T]):
    year: ComparisonFilterLookup[int] | None = UNSET
    month: ComparisonFilterLookup[int] | None = UNSET
    day: ComparisonFilterLookup[int] | None = UNSET
    week_day: ComparisonFilterLookup[int] | None = UNSET
    iso_week_day: ComparisonFilterLookup[int] | None = UNSET
    week: ComparisonFilterLookup[int] | None = UNSET
    iso_year: ComparisonFilterLookup[int] | None = UNSET
    quarter: ComparisonFilterLookup[int] | None = UNSET


@strawberry.input
class TimeFilterLookup(ComparisonFilterLookup[T]):
    hour: ComparisonFilterLookup[int] | None = UNSET
    minute: ComparisonFilterLookup[int] | None = UNSET
    second: ComparisonFilterLookup[int] | None = UNSET
    date: ComparisonFilterLookup[int] | None = UNSET
    time: ComparisonFilterLookup[int] | None = UNSET


@strawberry.input
class DatetimeFilterLookup(DateFilterLookup[T], TimeFilterLookup[T]):
    pass


type_filter_map = {
    strawberry.ID: BaseFilterLookup,
    bool: BaseFilterLookup,
    datetime.date: DateFilterLookup,
    datetime.datetime: DatetimeFilterLookup,
    datetime.time: TimeFilterLookup,
    decimal.Decimal: ComparisonFilterLookup,
    float: ComparisonFilterLookup,
    int: ComparisonFilterLookup,
    str: FilterLookup,
    uuid.UUID: FilterLookup,
}
