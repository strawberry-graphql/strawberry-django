import dataclasses
import strawberry
from strawberry.arguments import UNSET, is_unset, StrawberryArgument
from typing import List

from . import utils
from .arguments import argument

@strawberry.input
class OffsetPaginationInput:
    offset: int = 0
    limit: int = -1

def apply(pagination, queryset):
    if is_unset(pagination) or pagination is None:
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
            if pagination and not is_unset(pagination):
                arguments.append(
                    argument('pagination', OffsetPaginationInput)
                )
        return super().arguments + arguments

    def get_pagination(self):
        if not is_unset(self.pagination):
            return self.pagination
        type_ = self.type or self.child.type
        if utils.is_django_type(type_):
            return type_._django_type.pagination
        return None

    def get_queryset(self, queryset, info, pagination=UNSET, **kwargs):
        queryset = apply(pagination, queryset)
        return super().get_queryset(queryset, info, **kwargs)
