from typing import List

import strawberry
from strawberry import UNSET
from strawberry.arguments import StrawberryArgument

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

    def get_pagination(self):
        if self.pagination is not UNSET:
            return self.pagination

        type_ = utils.unwrap_type(self.type or self.child.type)
        if utils.is_django_type(type_):
            return type_._django_type.pagination
        return None

    def get_queryset(self, queryset, info, pagination=UNSET, **kwargs):
        queryset = super().get_queryset(queryset, info, **kwargs)
        return apply(pagination, queryset)
