import sys
import warnings
from typing import Generic, Optional, TypeVar, Union, cast

import strawberry
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count, QuerySet, Window
from django.db.models.functions import RowNumber
from django.db.models.query import MAX_GET_RESULTS  # type: ignore
from strawberry.types import Info
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.unset import UNSET, UnsetType
from typing_extensions import Self

from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.resolvers import django_resolver

from .arguments import argument
from .settings import strawberry_django_settings

NodeType = TypeVar("NodeType")
_QS = TypeVar("_QS", bound=QuerySet)

PAGINATION_ARG = "pagination"


@strawberry.type
class OffsetPaginationInfo:
    offset: int = 0
    limit: Optional[int] = UNSET


@strawberry.input
class OffsetPaginationInput(OffsetPaginationInfo): ...


@strawberry.type
class OffsetPaginated(Generic[NodeType]):
    queryset: strawberry.Private[Optional[QuerySet]]
    pagination: strawberry.Private[OffsetPaginationInput]

    @strawberry.field
    def page_info(self) -> OffsetPaginationInfo:
        return OffsetPaginationInfo(
            limit=self.pagination.limit,
            offset=self.pagination.offset,
        )

    @strawberry.field(description="Total count of existing results.")
    @django_resolver
    def total_count(self) -> int:
        return self.get_total_count()

    @strawberry.field(description="List of paginated results.")
    @django_resolver
    def results(self) -> list[NodeType]:
        paginated_queryset = self.get_paginated_queryset()

        return cast(
            "list[NodeType]",
            paginated_queryset if paginated_queryset is not None else [],
        )

    @classmethod
    def resolve_paginated(
        cls,
        queryset: QuerySet,
        *,
        info: Info,
        pagination: Optional[OffsetPaginationInput] = None,
        **kwargs,
    ) -> Self:
        """Resolve the paginated queryset.

        Args:
            queryset: The queryset to be paginated.
            info: The strawberry execution info resolve the type name from.
            pagination: The pagination input to be applied.
            kwargs: Additional arguments passed to the resolver.

        Returns:
            The resolved `OffsetPaginated`

        """
        return cls(
            queryset=queryset,
            pagination=pagination or OffsetPaginationInput(),
        )

    def get_total_count(self) -> int:
        """Retrieve tht total count of the queryset without pagination."""
        return get_total_count(self.queryset) if self.queryset is not None else 0

    def get_paginated_queryset(self) -> Optional[QuerySet]:
        """Retrieve the queryset with pagination applied.

        This will apply the paginated arguments to the queryset and return it.
        To use the original queryset, access `.queryset` directly.
        """
        from strawberry_django.optimizer import is_optimized_by_prefetching

        if self.queryset is None:
            return None

        return (
            self.queryset._result_cache  # type: ignore
            if is_optimized_by_prefetching(self.queryset)
            else apply(self.pagination, self.queryset)
        )


def apply(
    pagination: Optional[object],
    queryset: _QS,
    *,
    related_field_id: Optional[str] = None,
) -> _QS:
    """Apply pagination to a queryset.

    Args:
    ----
        pagination: The pagination input.
        queryset: The queryset to apply pagination to.
        related_field_id: The related field id to apply pagination to.
          When provided, the pagination will be applied using window functions
          instead of slicing the queryset.
          Useful for prefetches, as those cannot be sliced after being filtered

    """
    if pagination in (None, strawberry.UNSET):  # noqa: PLR6201
        return queryset

    if not isinstance(pagination, OffsetPaginationInput):
        raise TypeError(f"Don't know how to resolve pagination {pagination!r}")

    if related_field_id is not None:
        queryset = apply_window_pagination(
            queryset,
            related_field_id=related_field_id,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    else:
        start = pagination.offset
        limit = pagination.limit
        if limit is UNSET:
            settings = strawberry_django_settings()
            limit = settings["PAGINATION_DEFAULT_LIMIT"]

        if limit is not None and limit >= 0:
            stop = start + limit
            queryset = queryset[start:stop]
        else:
            queryset = queryset[start:]

    return queryset


class _PaginationWindow(Window):
    """Window function to be used for pagination.

    This is the same as django's `Window` function, but we can easily identify
    it in case we need to remove it from the queryset, as there might be other
    window functions in the queryset and no other way to identify ours.
    """


def apply_window_pagination(
    queryset: _QS,
    *,
    related_field_id: str,
    offset: int = 0,
    limit: Optional[int] = UNSET,
    max_results: Optional[int] = None,
) -> _QS:
    """Apply pagination using window functions.

    Useful for prefetches, as those cannot be sliced after being filtered.

    This is based on the same solution that Django uses, which was implemented
    in https://github.com/django/django/pull/15957

    Args:
    ----
        queryset: The queryset to apply pagination to.
        related_field_id: The related field id to apply pagination to.
        offset: The offset to start the pagination from.
        limit: The limit of items to return.

    """
    order_by = [
        expr
        for expr, _ in queryset.query.get_compiler(
            using=queryset._db or DEFAULT_DB_ALIAS  # type: ignore
        ).get_order_by()
    ]

    queryset = queryset.annotate(
        _strawberry_row_number=_PaginationWindow(
            RowNumber(),
            partition_by=related_field_id,
            order_by=order_by,
        ),
        _strawberry_total_count=_PaginationWindow(
            Count(1),
            partition_by=related_field_id,
        ),
    )

    if offset:
        queryset = queryset.filter(_strawberry_row_number__gt=offset)

    if limit is UNSET:
        settings = strawberry_django_settings()
        limit = (
            max_results
            if max_results is not None
            else settings["PAGINATION_DEFAULT_LIMIT"]
        )

    # Limit == -1 means no limit. sys.maxsize is set by relay when paginating
    # from the end to as a way to mimic a "not limit" as well
    if limit is not None and limit >= 0 and limit != sys.maxsize:
        queryset = queryset.filter(_strawberry_row_number__lte=offset + limit)

    return queryset


def remove_window_pagination(queryset: _QS) -> _QS:
    """Remove pagination window functions from a queryset.

    Utility function to remove the pagination `WHERE` clause added by
    the `apply_window_pagination` function.

    Args:
    ----
        queryset: The queryset to apply pagination to.

    """
    queryset = queryset._chain()  # type: ignore
    queryset.query.where.children = [
        child
        for child in queryset.query.where.children
        if (not hasattr(child, "lhs") or not isinstance(child.lhs, _PaginationWindow))
    ]
    return queryset


def get_total_count(queryset: QuerySet) -> int:
    """Get the total count of a queryset.

    Try to get the total count from the queryset cache, if it's optimized by
    prefetching. Otherwise, fallback to the `QuerySet.count()` method.
    """
    from strawberry_django.optimizer import is_optimized_by_prefetching

    if is_optimized_by_prefetching(queryset):
        results = queryset._result_cache  # type: ignore

        if results:
            try:
                return results[0]._strawberry_total_count
            except AttributeError:
                warnings.warn(
                    (
                        "Pagination annotations not found, falling back to QuerySet resolution. "
                        "This might cause n+1 issues..."
                    ),
                    RuntimeWarning,
                    stacklevel=2,
                )

        # If we have no results, we can't get the total count from the cache.
        # In this case we will remove the pagination filter to be able to `.count()`
        # the whole queryset with its original filters.
        queryset = remove_window_pagination(queryset)

    return queryset.count()


class StrawberryDjangoPagination(StrawberryDjangoFieldBase):
    def __init__(self, pagination: Union[bool, UnsetType] = UNSET, **kwargs):
        self.pagination = pagination
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.pagination = self.pagination
        return new_field

    def _has_pagination(self) -> bool:
        if isinstance(self.pagination, bool):
            return self.pagination

        if self.is_paginated:
            return True

        django_type = self.django_type
        if django_type is not None and not issubclass(
            django_type, strawberry.relay.Node
        ):
            return django_type.__strawberry_django_definition__.pagination

        return False

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if (
            self.base_resolver is None
            and (self.is_list or self.is_paginated)
            and not self.is_model_property
        ):
            pagination = self.get_pagination()
            if pagination is not None:
                arguments.append(
                    argument("pagination", OffsetPaginationInput, is_optional=True),
                )
        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(StrawberryDjangoPagination, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_pagination(self) -> Optional[type]:
        return OffsetPaginationInput if self._has_pagination() else None

    def apply_pagination(
        self,
        queryset: _QS,
        pagination: Optional[object] = None,
        *,
        related_field_id: Optional[str] = None,
    ) -> _QS:
        return apply(pagination, queryset, related_field_id=related_field_id)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        *,
        pagination: Optional[OffsetPaginationInput] = None,
        _strawberry_related_field_id: Optional[str] = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)

        # If the queryset is not ordered, and this field is either going to return
        # multiple records, or call `.first()`, then order by the primary key to ensure
        # deterministic results.
        if not queryset.ordered and (
            self.is_list or self.is_paginated or self.is_connection or self.is_optional
        ):
            queryset = queryset.order_by("pk")

        # This is counter intuitive, but in case we are returning a `Paginated`
        # result, we want to set the original queryset _as is_ as it will apply
        # the pagination later on when resolving its `.results` field.
        # Check `get_wrapped_result` below for more details.
        if self.is_paginated:
            return queryset

        # Add implicit pagination if this field is not a list
        # that way when first() / get() is called on the QuerySet it does not cause extra queries
        # and we don't prefetch more than necessary
        if (
            not pagination
            and not (self.is_list or self.is_paginated or self.is_connection)
            and not _strawberry_related_field_id
        ):
            if self.is_optional:
                pagination = OffsetPaginationInput(offset=0, limit=1)
            else:
                pagination = OffsetPaginationInput(offset=0, limit=MAX_GET_RESULTS)

        return self.apply_pagination(
            queryset,
            pagination,
            related_field_id=_strawberry_related_field_id,
        )
