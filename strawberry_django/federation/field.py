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
from strawberry.types.field import _RESOLVER_TYPE

from strawberry_django.fields.field import StrawberryDjangoField

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from strawberry import BasePermission
    from strawberry.federation.schema_directives import Override
    from strawberry.types.unset import UnsetType

    from strawberry_django.utils.typing import (
        AnnotateType,
        PrefetchType,
        TypeOrMapping,
        TypeOrSequence,
    )


__all__ = ["field"]


def _process_federation_field_params(
    directives: Sequence[object] | None,
    *,
    authenticated: bool,
    external: bool,
    inaccessible: bool,
    policy: list[list[str]] | None,
    provides: list[str] | None,
    override: Override | str | None,
    requires: list[str] | None,
    requires_scopes: list[list[str]] | None,
    shareable: bool,
    tags: Sequence[str] | None,
) -> list[object]:
    """Convert federation field parameters to directives.

    Follows the same pattern as strawberry.federation.field.
    """
    from strawberry.federation.schema_directives import (
        Authenticated,
        External,
        Inaccessible,
        Override,
        Policy,
        Provides,
        Requires,
        RequiresScopes,
        Shareable,
        Tag,
    )
    from strawberry.federation.types import FieldSet

    result_directives = list(directives or [])

    if authenticated:
        result_directives.append(Authenticated())

    if external:
        result_directives.append(External())

    if inaccessible:
        result_directives.append(Inaccessible())

    if override:
        if isinstance(override, str):
            result_directives.append(Override(override_from=override, label=UNSET))
        else:
            result_directives.append(override)

    if policy:
        result_directives.append(Policy(policies=policy))

    if provides:
        result_directives.append(Provides(fields=FieldSet(" ".join(provides))))

    if requires:
        result_directives.append(Requires(fields=FieldSet(" ".join(requires))))

    if requires_scopes:
        result_directives.append(RequiresScopes(scopes=requires_scopes))

    if shareable:
        result_directives.append(Shareable())

    if tags:
        result_directives.extend(Tag(name=tag) for tag in tags)

    return result_directives


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
    # Federation-specific parameters
    authenticated: bool = False,
    external: bool = False,
    inaccessible: bool = False,
    policy: list[list[str]] | None = None,
    provides: list[str] | None = None,
    override: Override | str | None = None,
    requires: list[str] | None = None,
    requires_scopes: list[list[str]] | None = None,
    shareable: bool = False,
    tags: Sequence[str] | None = None,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
) -> Any:
    """Annotate a method or property as a federated Django GraphQL field.

    Wraps `strawberry_django.field` with federation-specific parameters.

    Federation-specific args:
        authenticated, external, inaccessible, policy, provides, override,
        requires, requires_scopes, shareable, tags.

    See `strawberry_django.field` for all other parameters.
    """
    # Process federation parameters into directives
    processed_directives = _process_federation_field_params(
        directives,
        authenticated=authenticated,
        external=external,
        inaccessible=inaccessible,
        policy=policy,
        provides=provides,
        override=override,
        requires=requires,
        requires_scopes=requires_scopes,
        shareable=shareable,
        tags=tags,
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
