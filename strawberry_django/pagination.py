from typing import TYPE_CHECKING, List, Optional, TypeVar, Union

import strawberry
from strawberry.arguments import StrawberryArgument
from strawberry.types import Info
from strawberry.unset import UNSET, UnsetType
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


def apply(pagination: Optional[object], queryset: _QS) -> _QS:
    if pagination in (None, strawberry.UNSET):  # noqa: PLR6201
        return queryset

    if not isinstance(pagination, OffsetPaginationInput):
        raise TypeError(f"Don't know how to resolve pagination {pagination!r}")

    start = pagination.offset
    stop = start + pagination.limit

    return queryset[start:stop]


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
    ) -> _QS:
        return apply(pagination, queryset)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        pagination: Optional[object] = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_pagination(queryset, pagination)
