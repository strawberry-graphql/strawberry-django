import sys
from typing import TYPE_CHECKING, List, Optional, TypeVar, Union

import strawberry
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count, Window
from django.db.models.functions import RowNumber
from strawberry.types import Info
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.unset import UNSET, UnsetType
from typing_extensions import Self

from strawberry_django.fields.base import StrawberryDjangoFieldBase

from .arguments import argument

if TYPE_CHECKING:
    from django.db.models import QuerySet

_QS = TypeVar("_QS", bound="QuerySet")


@strawberry.input
class OffsetPaginationInput:
    offset: int = 0
    limit: int = -1


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
        stop = start + pagination.limit
        queryset = queryset[start:stop]

    return queryset


def apply_window_pagination(
    queryset: _QS,
    *,
    related_field_id: str,
    offset: int = 0,
    limit: int = -1,
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
        _strawberry_row_number=Window(
            RowNumber(),
            partition_by=related_field_id,
            order_by=order_by,
        ),
        _strawberry_total_count=Window(
            Count(1),
            partition_by=related_field_id,
        ),
    )

    if offset:
        queryset = queryset.filter(_strawberry_row_number__gt=offset)

    # Limit == -1 means no limit. sys.maxsize is set by relay when paginating
    # from the end to as a way to mimic a "not limit" as well
    if limit >= 0 and limit != sys.maxsize:
        queryset = queryset.filter(_strawberry_row_number__lte=offset + limit)

    return queryset


class StrawberryDjangoPagination(StrawberryDjangoFieldBase):
    def __init__(self, pagination: Union[bool, UnsetType] = UNSET, **kwargs):
        self.pagination = pagination
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.pagination = self.pagination
        return new_field

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and self.is_list:
            pagination = self.get_pagination()
            if pagination is not None:
                arguments.append(
                    argument("pagination", OffsetPaginationInput, is_optional=True),
                )
        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: List[StrawberryArgument]):
        args_prop = super(StrawberryDjangoPagination, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_pagination(self) -> Optional[type]:
        has_pagination = self.pagination

        if isinstance(has_pagination, UnsetType):
            django_type = self.django_type
            has_pagination = (
                django_type.__strawberry_django_definition__.pagination
                if (
                    django_type is not None
                    and not issubclass(django_type, strawberry.relay.Node)
                )
                else False
            )

        return OffsetPaginationInput if has_pagination else None

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
        pagination: Optional[object] = None,
        _strawberry_related_field_id: Optional[str] = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_pagination(
            queryset,
            pagination,
            related_field_id=_strawberry_related_field_id,
        )
