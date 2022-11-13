from typing import List, Optional, Type

import strawberry
from django.db.models import QuerySet
from strawberry import UNSET
from strawberry.arguments import StrawberryArgument
from strawberry.types import Info

from . import utils
from .arguments import argument


@strawberry.input
class OffsetPaginationInput:
    offset: int = 0
    limit: int = -1


def apply(pagination, queryset):
    if pagination is UNSET or pagination is None:
        return queryset

    start = pagination.offset
    stop = start + pagination.limit
    return queryset[start:stop]


class StrawberryDjangoPagination:
    def __init__(self, pagination=UNSET, **kwargs):
        self.pagination = pagination
        super().__init__(**kwargs)

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if not self.base_resolver:
            pagination = self.get_pagination()
            if pagination and pagination is not UNSET:
                arguments.append(argument("pagination", OffsetPaginationInput))
        return super().arguments + arguments

    def get_pagination(self) -> Optional[Type]:
        if self.pagination is not UNSET:
            return self.pagination

        type_ = utils.unwrap_type(self.type or self.child.type)
        if utils.is_django_type(type_):
            return type_._django_type.pagination
        return None

    def apply_pagination(self, queryset: QuerySet, pagination=UNSET):
        return apply(pagination, queryset)

    def get_queryset(
        self, queryset: QuerySet, info: Info, pagination: Type = UNSET, **kwargs
    ):
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_pagination(queryset, pagination)
