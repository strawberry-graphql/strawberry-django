"""Federation field decorator for Django models.

This module provides a federation-aware field decorator that wraps
`strawberry_django.field` with federation-specific parameters like
`external`, `requires`, `provides`, etc.
"""

from __future__ import annotations

import dataclasses
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
)

from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.extensions.field_extension import FieldExtension
from strawberry.federation.params import (
    FederationFieldParams,
    process_federation_field_directives,
)
from strawberry.types.field import _RESOLVER_TYPE
from typing_extensions import Unpack

from strawberry_django.fields.field import StrawberryDjangoField

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from strawberry import BasePermission
    from strawberry.types.unset import UnsetType

    from strawberry_django.utils.typing import (
        AnnotateType,
        PrefetchType,
        TypeOrMapping,
        TypeOrSequence,
    )


__all__ = ["field"]


def field(
    resolver: _RESOLVER_TYPE[Any] | None = None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: Sequence[FieldExtension] = (),
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    ordering: type | UnsetType | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
    **federation_kwargs: Unpack[FederationFieldParams],
) -> Any:
    """Annotate a method or property as a federated Django GraphQL field.

    Wraps `strawberry_django.field` with federation-specific parameters.

    Federation-specific args:
        authenticated, external, inaccessible, policy, provides, override,
        requires, requires_scopes, shareable, tags.

    See `strawberry_django.field` for all other parameters.
    """
    processed_directives = process_federation_field_directives(
        directives, **federation_kwargs
    )

    if order:
        warnings.warn(
            "strawberry_django.order is deprecated in favor of strawberry_django.order_type.",
            DeprecationWarning,
            stacklevel=2,
        )

    f = field_cls(
        python_name=None,
        django_name=field_name,
        graphql_name=name,
        type_annotation=StrawberryAnnotation.from_annotation(graphql_type),
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=processed_directives,
        filters=filters,
        pagination=pagination,
        order=order,
        ordering=ordering,
        extensions=extensions,
        only=only,
        select_related=select_related,
        prefetch_related=prefetch_related,
        annotate=annotate,
        disable_optimization=disable_optimization,
    )

    if resolver:
        return f(resolver)

    return f
