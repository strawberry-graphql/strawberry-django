import dataclasses
from typing import List, Optional, Union

import strawberry
from strawberry.arguments import UNSET, StrawberryArgument, is_unset

from . import utils
from .arguments import argument


@dataclasses.dataclass
class PaginationConfig:
    default_offset: int = 0
    default_limit: Optional[int] = None
    max_limit: Optional[int] = None


PaginationConfigArgType = Union[PaginationConfig, None, UNSET.__class__]


@strawberry.input
class OffsetPaginationInput:
    offset: int = 0
    limit: int = -1


def apply(pagination, pagination_config, queryset):
    offset = None
    limit = None

    if pagination and not is_unset(pagination):
        offset = pagination.offset
        limit = pagination.limit if pagination.limit != -1 else None

    if pagination_config and not is_unset(pagination_config):
        if offset is None:
            offset = pagination_config.default_offset
        if limit is None:
            limit = pagination_config.default_limit
        if pagination_config.max_limit is not None:
            if limit is None:
                limit = pagination_config.max_limit
            else:
                limit = min(limit, pagination_config.max_limit)

    if offset is not None and limit is not None:
        stop = offset + limit
        queryset = queryset[offset:stop]
    elif offset is not None:
        queryset = queryset[offset:]
    elif limit is not None:
        queryset = queryset[:limit]

    return queryset


class StrawberryDjangoPagination:
    def __init__(
        self,
        pagination=UNSET,
        pagination_config: PaginationConfigArgType = UNSET,
        **kwargs,
    ):
        self.pagination = pagination
        self.pagination_config = pagination_config
        super().__init__(**kwargs)

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if not self.base_resolver:
            pagination = self.get_pagination()
            if pagination and not is_unset(pagination):
                arguments.append(argument("pagination", OffsetPaginationInput))
        return super().arguments + arguments

    def get_pagination(self):
        if not is_unset(self.pagination):
            return self.pagination
        type_ = utils.unwrap_type(self.type or self.child.type)
        if utils.is_django_type(type_):
            return type_._django_type.pagination
        return None

    def get_pagination_config(self) -> Optional[PaginationConfig]:
        if not is_unset(self.pagination_config):
            return self.pagination_config
        type_ = utils.unwrap_type(self.type or self.child.type)
        if utils.is_django_type(type_):
            return type_._django_type.pagination_config
        return None

    def get_queryset(self, queryset, info, pagination=UNSET, **kwargs):
        pagination_config = self.get_pagination_config()
        queryset = apply(pagination, pagination_config, queryset)
        return super().get_queryset(queryset, info, **kwargs)
