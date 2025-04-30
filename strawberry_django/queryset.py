from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, TypeVar

from django.db.models import Model
from django.db.models.query import QuerySet

if TYPE_CHECKING:
    from strawberry import Info

    from strawberry_django.relay.cursor_connection import OrderingDescriptor

_M = TypeVar("_M", bound=Model)

CONFIG_KEY = "_strawberry_django_config"


@dataclasses.dataclass
class StrawberryDjangoQuerySetConfig:
    optimized: bool = False
    optimized_by_prefetching: bool = False
    type_get_queryset_did_run: bool = False
    ordering_descriptors: list[OrderingDescriptor] | None = None


def get_queryset_config(queryset: QuerySet) -> StrawberryDjangoQuerySetConfig:
    config = getattr(queryset, CONFIG_KEY, None)
    if config is None:
        setattr(queryset, CONFIG_KEY, (config := StrawberryDjangoQuerySetConfig()))
    return config


def run_type_get_queryset(
    qs: QuerySet[_M],
    origin: Any,
    info: Info | None = None,
) -> QuerySet[_M]:
    config = get_queryset_config(qs)
    get_queryset = getattr(origin, "get_queryset", None)

    if get_queryset and not config.type_get_queryset_did_run:
        qs = get_queryset(qs, info)
        new_config = get_queryset_config(qs)
        new_config.type_get_queryset_did_run = True

    return qs


_original_clone = QuerySet._clone  # type: ignore


def _qs_clone(self):
    config = get_queryset_config(self)
    cloned = _original_clone(self)
    setattr(cloned, CONFIG_KEY, dataclasses.replace(config))
    return cloned


# Monkey patch the QuerySet._clone method to make sure our config is copied
# to the new QuerySet instance once it is cloned.
QuerySet._clone = _qs_clone  # type: ignore
