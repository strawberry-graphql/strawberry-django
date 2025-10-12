import dataclasses
from collections.abc import Callable, Mapping, Sequence
from typing import (
    Any,
    Literal,
    TypeVar,
    overload,
)

from strawberry.annotation import StrawberryAnnotation
from strawberry.extensions.field_extension import FieldExtension
from strawberry.field_extensions import InputMutationExtension
from strawberry.permission import BasePermission
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry.types.unset import UNSET, UnsetType

from .fields import (
    DjangoCreateMutation,
    DjangoDeleteMutation,
    DjangoMutationBase,
    DjangoUpdateMutation,
)
from .types import FullCleanOptions

_T = TypeVar("_T")


@overload
def mutation(
    *,
    resolver: Callable[[], _T],
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[False] = False,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> _T: ...


@overload
def mutation(
    *,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> Any: ...


@overload
def mutation(
    resolver: StrawberryResolver | Callable | staticmethod | classmethod,
    *,
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
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> DjangoMutationBase: ...


def mutation(
    resolver=None,
    *,
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
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
) -> Any:
    """Annotate a property or a method to create a mutation field."""
    f = DjangoMutationBase(
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
        directives=directives,
        extensions=extensions or (),
        handle_django_errors=handle_django_errors,
    )

    if resolver is not None:
        return f(resolver)

    return f


@overload
def input_mutation(
    *,
    resolver: Callable[[], _T],
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[False] = False,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> _T: ...


@overload
def input_mutation(
    *,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> Any: ...


@overload
def input_mutation(
    resolver: StrawberryResolver | Callable | staticmethod | classmethod,
    *,
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
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
) -> DjangoMutationBase: ...


def input_mutation(
    resolver=None,
    *,
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
    extensions: list[FieldExtension] | None = None,
    handle_django_errors: bool | None = None,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
) -> Any:
    """Annotate a property or a method to create an input mutation field."""
    extensions = [*(extensions or []), InputMutationExtension()]
    f = DjangoMutationBase(
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
        directives=directives,
        extensions=extensions,
        handle_django_errors=handle_django_errors,
    )

    if resolver is not None:
        return f(resolver)

    return f


def create(
    input_type: type | None = None,
    *,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    argument_name: str | None = None,
    handle_django_errors: bool | None = None,
    full_clean: bool | FullCleanOptions = True,
) -> Any:
    """Create mutation for django input fields.

    Automatically create data for django input fields.

    Examples
    --------
        >>> @strawberry.django.input
        ... class ProductInput:
        ...     name: strawberry.auto
        ...     price: strawberry.auto
        ...
        >>> @strawberry.mutation
        >>> class Mutation:
        ...     create_product: ProductType = strawberry.django.create_mutation(
        ...         ProductInput
        ...     )

    """
    return DjangoCreateMutation(
        input_type,
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
        directives=directives,
        extensions=extensions or (),
        argument_name=argument_name,
        handle_django_errors=handle_django_errors,
        full_clean=full_clean,
    )


def update(
    input_type: type | None = None,
    *,
    name: str | None = None,
    field_name: str | None = None,
    filters: type | UnsetType | None = UNSET,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] | None = None,
    argument_name: str | None = None,
    handle_django_errors: bool | None = None,
    key_attr: str | None = None,
    full_clean: bool | FullCleanOptions = True,
) -> Any:
    """Update mutation for django input fields.

    Examples
    --------
        >>> @strawberry.django.input
        ... class ProductInput(IdInput):
        ...     name: strawberry.auto
        ...     price: strawberry.auto
        ...
        >>> @strawberry.mutation
        >>> class Mutation:
        ...     create_product: ProductType = strawberry.django.update_mutation(
        ...         ProductInput
        ...     )

    """
    return DjangoUpdateMutation(
        input_type,
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
        directives=directives,
        filters=filters,
        extensions=extensions or (),
        argument_name=argument_name,
        handle_django_errors=handle_django_errors,
        key_attr=key_attr,
        full_clean=full_clean,
    )


def delete(
    input_type: type | None = None,
    *,
    name: str | None = None,
    field_name: str | None = None,
    filters: type | UnsetType | None = UNSET,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] | None = None,
    graphql_type: Any | None = None,
    argument_name: str | None = None,
    handle_django_errors: bool | None = None,
    key_attr: str | None = None,
    full_clean: bool | FullCleanOptions = True,
) -> Any:
    return DjangoDeleteMutation(
        input_type=input_type,
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
        directives=directives,
        filters=filters,
        extensions=extensions or (),
        argument_name=argument_name,
        handle_django_errors=handle_django_errors,
        key_attr=key_attr,
        full_clean=full_clean,
    )
