"""Federation reference resolution utilities for Django models.

This module provides utilities to automatically generate `resolve_reference`
class methods for federation entity types backed by Django models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.db import models
from strawberry.types.info import Info
from strawberry.utils.await_maybe import AwaitableOrValue

from strawberry_django.queryset import run_type_get_queryset
from strawberry_django.resolvers import django_resolver

if TYPE_CHECKING:
    from strawberry_django.utils.typing import WithStrawberryDjangoObjectDefinition

_M = TypeVar("_M", bound=models.Model)


__all__ = [
    "generate_resolve_reference",
    "resolve_model_reference",
]


def resolve_model_reference(
    source: type[WithStrawberryDjangoObjectDefinition],
    *,
    info: Info | None = None,
    **key_fields: Any,
) -> AwaitableOrValue[_M]:
    """Resolve a Django model instance by federation key fields.

    Similar to `resolve_model_node` but works with arbitrary key fields.
    """
    from strawberry_django import optimizer  # avoid circular import
    from strawberry_django.utils.typing import get_django_definition

    django_type = get_django_definition(source, strict=True)
    model = cast("type[_M]", django_type.model)

    qs = model._default_manager.all()
    qs = run_type_get_queryset(qs, source, info)
    qs = qs.filter(**key_fields)

    if info is not None:
        ext = optimizer.optimizer.get()
        if ext is not None:
            # If optimizer extension is enabled, optimize this queryset
            qs = ext.optimize(qs, info=info)

    def _get_result() -> _M:
        return qs.get()

    return django_resolver(_get_result)()


def generate_resolve_reference(key_fields: list[str]) -> classmethod:
    """Generate a resolve_reference classmethod for a federation entity type.

    Only *key_fields* are forwarded to the ORM query — federation may pass
    extra fields (e.g. from @requires) that are not valid ORM lookups.
    """

    def resolve_reference(
        cls: type[WithStrawberryDjangoObjectDefinition],
        info: Info | None = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Any]:
        # Extract only the key fields from kwargs
        # (federation may pass additional fields)
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in key_fields}
        return resolve_model_reference(cls, info=info, **filtered_kwargs)

    return classmethod(resolve_reference)
