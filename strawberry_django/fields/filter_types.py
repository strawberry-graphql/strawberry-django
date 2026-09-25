import datetime
import decimal
import uuid
import warnings
from typing import (
    Any,
    Generic,
    TypeVar,
)

import strawberry
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from strawberry import UNSET

from strawberry_django.filters import resolve_value

from .filter_order import filter_field

T = TypeVar("T")

_SKIP_MSG = "Filter will be skipped on `null` value"


def _warn_concrete_lookup(cls: type) -> None:
    warnings.warn(
        f"{cls.__name__} is not generic; the type argument is ignored. "
        "Use the bare class instead.",
        DeprecationWarning,
        stacklevel=3,
    )


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

    def __class_getitem__(cls, item: Any) -> Any:
        if item is str or item is uuid.UUID:
            warnings.warn(
                f"FilterLookup[{item.__name__}] may cause DuplicatedTypeName errors. "
                "Use StrFilterLookup instead.",
                UserWarning,
                stacklevel=2,
            )
        return super().__class_getitem__(item)  # type: ignore[misc]


@strawberry.input
class StrFilterLookup(BaseFilterLookup[str]):
    i_exact: str | None = filter_field(
        description=f"Case-insensitive exact match. {_SKIP_MSG}"
    )
    contains: str | None = filter_field(
        description=f"Case-sensitive containment test. {_SKIP_MSG}"
    )
    i_contains: str | None = filter_field(
        description=f"Case-insensitive containment test. {_SKIP_MSG}"
    )
    starts_with: str | None = filter_field(
        description=f"Case-sensitive starts-with. {_SKIP_MSG}"
    )
    i_starts_with: str | None = filter_field(
        description=f"Case-insensitive starts-with. {_SKIP_MSG}"
    )
    ends_with: str | None = filter_field(
        description=f"Case-sensitive ends-with. {_SKIP_MSG}"
    )
    i_ends_with: str | None = filter_field(
        description=f"Case-insensitive ends-with. {_SKIP_MSG}"
    )
    regex: str | None = filter_field(
        description=f"Case-sensitive regular expression match. {_SKIP_MSG}"
    )
    i_regex: str | None = filter_field(
        description=f"Case-insensitive regular expression match. {_SKIP_MSG}"
    )

    def __class_getitem__(cls, item: Any) -> type:
        _warn_concrete_lookup(cls)
        return cls


@strawberry.input
class DateFilterLookup(ComparisonFilterLookup[datetime.date]):
    year: ComparisonFilterLookup[int] | None = UNSET
    month: ComparisonFilterLookup[int] | None = UNSET
    day: ComparisonFilterLookup[int] | None = UNSET
    week_day: ComparisonFilterLookup[int] | None = UNSET
    iso_week_day: ComparisonFilterLookup[int] | None = UNSET
    week: ComparisonFilterLookup[int] | None = UNSET
    iso_year: ComparisonFilterLookup[int] | None = UNSET
    quarter: ComparisonFilterLookup[int] | None = UNSET

    def __class_getitem__(cls, item: Any) -> type:
        _warn_concrete_lookup(cls)
        return cls


@strawberry.input
class TimeFilterLookup(ComparisonFilterLookup[datetime.time]):
    hour: ComparisonFilterLookup[int] | None = UNSET
    minute: ComparisonFilterLookup[int] | None = UNSET
    second: ComparisonFilterLookup[int] | None = UNSET

    def __class_getitem__(cls, item: Any) -> type:
        _warn_concrete_lookup(cls)
        return cls


@strawberry.input
class DatetimeFilterLookup(ComparisonFilterLookup[datetime.datetime]):
    year: ComparisonFilterLookup[int] | None = UNSET
    month: ComparisonFilterLookup[int] | None = UNSET
    day: ComparisonFilterLookup[int] | None = UNSET
    week_day: ComparisonFilterLookup[int] | None = UNSET
    iso_week_day: ComparisonFilterLookup[int] | None = UNSET
    week: ComparisonFilterLookup[int] | None = UNSET
    iso_year: ComparisonFilterLookup[int] | None = UNSET
    quarter: ComparisonFilterLookup[int] | None = UNSET
    hour: ComparisonFilterLookup[int] | None = UNSET
    minute: ComparisonFilterLookup[int] | None = UNSET
    second: ComparisonFilterLookup[int] | None = UNSET
    date: ComparisonFilterLookup[datetime.date] | None = UNSET
    time: ComparisonFilterLookup[datetime.time] | None = UNSET

    def __class_getitem__(cls, item: Any) -> type:
        _warn_concrete_lookup(cls)
        return cls


type_filter_map: dict[type, type] = {
    strawberry.ID: BaseFilterLookup,  # type: ignore[dict-item]
    bool: BaseFilterLookup,
    datetime.date: DateFilterLookup,
    datetime.datetime: DatetimeFilterLookup,
    datetime.time: TimeFilterLookup,
    decimal.Decimal: ComparisonFilterLookup,
    float: ComparisonFilterLookup,
    int: ComparisonFilterLookup,
    str: StrFilterLookup,
    uuid.UUID: StrFilterLookup,
}

try:
    from django.contrib.gis import geos
except ImproperlyConfigured:
    # If gdal is not available, skip.
    GeometryFilterLookup = None  # type: ignore[assignment]
else:
    # Not based on BaseFilterLookup since the `in` lookup is not a spatial lookup
    # and would compare the raw geometry values instead.
    @strawberry.input
    class GeometryFilterLookup:
        exact: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially equal to the given geometry. {_SKIP_MSG}"
        )
        is_null: bool | None = filter_field(description=f"Assignment test. {_SKIP_MSG}")
        contains: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially contains the given geometry. {_SKIP_MSG}"
        )
        disjoint: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially disjoint from the given geometry. {_SKIP_MSG}"
        )
        equals: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially equal to the given geometry. {_SKIP_MSG}"
        )
        intersects: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially intersects the given geometry. {_SKIP_MSG}"
        )
        overlaps: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially overlaps the given geometry. {_SKIP_MSG}"
        )
        touches: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially touches the given geometry. {_SKIP_MSG}"
        )
        within: geos.GEOSGeometry | None = filter_field(
            description=f"Spatially within the given geometry. {_SKIP_MSG}"
        )

    type_filter_map.update(
        dict.fromkeys(
            (
                geos.Point,
                geos.LineString,
                geos.LinearRing,
                geos.Polygon,
                geos.MultiPoint,
                geos.MultiLineString,
                geos.MultiPolygon,
                geos.GEOSGeometry,
            ),
            GeometryFilterLookup,
        )
    )
