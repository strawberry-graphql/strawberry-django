"""Federation type decorators for Django models.

This module provides federation-aware type decorators that wrap
`strawberry_django.type` and `strawberry_django.interface` with
federation-specific parameters like `keys`, `shareable`, etc.
"""

from __future__ import annotations

import builtins
from typing import (
    TYPE_CHECKING,
    Literal,
    TypeVar,
)

from django.db.models import Model
from strawberry.federation.params import (
    FederationInterfaceParams,
    FederationTypeParams,
    process_federation_type_directives,
)
from strawberry.types.field import StrawberryField
from typing_extensions import Unpack, dataclass_transform

from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.fields.field import field as _field
from strawberry_django.type import _process_type

from .resolve import generate_resolve_reference

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from strawberry_django.utils.typing import (
        AnnotateType,
        PrefetchType,
        TypeOrMapping,
        TypeOrSequence,
    )

_T = TypeVar("_T", bound=builtins.type)


__all__ = [
    "interface",
    "type",
]


def _get_keys_from_directives(directives: Sequence[object]) -> list[str]:
    """Extract unique key field names from Key directives.

    Used to build the filter kwargs for resolve_reference — federation may
    pass extra fields (e.g. from @requires) that are not valid ORM lookups.
    """
    from strawberry.federation.schema_directives import Key

    key_fields: list[str] = []
    for directive in directives:
        if isinstance(directive, Key):
            fields = str(directive.fields).split()
            key_fields.extend(fields)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(key_fields))


def _maybe_add_resolve_reference(
    cls: builtins.type, directives: Sequence[object]
) -> None:
    """Add auto-generated resolve_reference if the type has @key directives."""
    key_fields = _get_keys_from_directives(directives)

    if not key_fields:
        return

    # Don't override existing resolve_reference defined on this class
    if "resolve_reference" in cls.__dict__:
        return

    # Generate and add resolve_reference
    resolve_ref = generate_resolve_reference(key_fields)
    cls.resolve_reference = resolve_ref


@dataclass_transform(
    kw_only_default=True,
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def type(  # noqa: A001
    model: builtins.type[Model],
    *,
    # Standard strawberry_django.type parameters
    name: str | None = None,
    field_cls: builtins.type[StrawberryDjangoField] = StrawberryDjangoField,
    is_input: bool = False,
    is_interface: bool = False,
    is_filter: Literal["lookups"] | bool = False,
    description: str | None = None,
    directives: Sequence[object] | None = (),
    filters: builtins.type | None = None,
    order: builtins.type | None = None,
    ordering: builtins.type | None = None,
    pagination: bool = False,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    fields: list[str] | Literal["__all__"] | None = None,
    exclude: list[str] | None = None,
    **federation_kwargs: Unpack[FederationTypeParams],
) -> Callable[[_T], _T]:
    """Annotate a class as a federated Django GraphQL type.

    Wraps `strawberry_django.type` with federation support, adding directives
    and auto-generating `resolve_reference` for entity types.

    Accepts all `strawberry_django.type` parameters plus federation-specific ones:

    Args:
        keys: Federation key fields (strings or Key directives).
        extend: Whether this type extends a type from another subgraph.
        shareable: Whether this type can be resolved by multiple subgraphs.
        inaccessible: Whether this type is hidden from the public API.
        authenticated: Whether this type requires authentication.
        policy: Access policy for this type.
        requires_scopes: Required scopes for this type.
        tags: Metadata tags for this type.

    """
    processed_directives, extend = process_federation_type_directives(
        directives, **federation_kwargs
    )

    def wrapper(cls: _T) -> _T:
        # Add auto-generated resolve_reference if needed
        _maybe_add_resolve_reference(cls, processed_directives)

        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_input=is_input,
            is_filter=is_filter,
            is_interface=is_interface,
            description=description,
            directives=processed_directives,
            extend=extend,
            filters=filters,
            pagination=pagination,
            order=order,
            ordering=ordering,
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
            annotate=annotate,
            disable_optimization=disable_optimization,
            fields=fields,
            exclude=exclude,
        )

    return wrapper


@dataclass_transform(
    kw_only_default=True,
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def interface(
    model: builtins.type[Model],
    *,
    # Standard strawberry_django.interface parameters
    name: str | None = None,
    field_cls: builtins.type[StrawberryDjangoField] = StrawberryDjangoField,
    description: str | None = None,
    directives: Sequence[object] | None = (),
    disable_optimization: bool = False,
    **federation_kwargs: Unpack[FederationInterfaceParams],
) -> Callable[[_T], _T]:
    """Annotate a class as a federated Django GraphQL interface.

    Wraps `strawberry_django.interface` with federation support.
    See `type()` for federation-specific parameters.
    """
    processed_directives, _ = process_federation_type_directives(
        directives, **federation_kwargs
    )

    def wrapper(cls: _T) -> _T:
        # Add auto-generated resolve_reference if needed
        _maybe_add_resolve_reference(cls, processed_directives)

        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_interface=True,
            description=description,
            directives=processed_directives,
            disable_optimization=disable_optimization,
        )

    return wrapper
