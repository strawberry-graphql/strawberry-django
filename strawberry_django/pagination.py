from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, TypeVar

import strawberry
from strawberry.unset import UNSET, UnsetType

from strawberry_django.fields.base import StrawberryDjangoFieldBase

from . import utils
from .arguments import argument

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from strawberry.arguments import StrawberryArgument
    from strawberry.type import StrawberryType
    from strawberry.types import Info
    from typing_extensions import Self

_QS = TypeVar("_QS", bound="QuerySet")


@strawberry.input
class OffsetPaginationInput:
    offset: int = 0
    limit: int = -1


def apply(pagination: type | None, queryset: _QS) -> _QS:
    if pagination in (None, strawberry.UNSET):
        return queryset

    if not isinstance(pagination, OffsetPaginationInput):
        raise TypeError(f"Don't know how to resolve pagination {pagination!r}")

    start = pagination.offset
    stop = start + pagination.limit

    return queryset[start:stop]


class StrawberryDjangoPagination(StrawberryDjangoFieldBase):
    def __init__(self, pagination: bool | UnsetType = UNSET, **kwargs):
        self.pagination = pagination
        super().__init__(**kwargs)

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and self.is_list:
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

    def copy_with(
        self,
        type_var_map: Mapping[TypeVar, StrawberryType | type],
    ) -> Self:
        new_field = super().copy_with(type_var_map)
        new_field.pagination = self.pagination
        return new_field

    def get_pagination(self) -> type | None:
        has_pagination = self.pagination

        if isinstance(has_pagination, UnsetType):
            type_ = utils.unwrap_type(self.type)
            has_pagination = (
                type_._django_type.pagination if utils.is_django_type(type_) else False
            )

        return OffsetPaginationInput if has_pagination else None

    def apply_pagination(self, queryset: _QS, pagination: type | None = None) -> _QS:
        return apply(pagination, queryset)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        pagination: type | None = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_pagination(queryset, pagination)
