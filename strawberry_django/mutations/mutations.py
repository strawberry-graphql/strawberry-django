import dataclasses
from collections.abc import Callable, Mapping, Sequence
from typing import (
    Any,
    Optional,
    TypeVar,
    Union,
    overload,
)

from strawberry.annotation import StrawberryAnnotation
from strawberry.extensions.field_extension import FieldExtension
from strawberry.field_extensions import InputMutationExtension
from strawberry.permission import BasePermission
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry.types.unset import UNSET, UnsetType
from typing_extensions import Literal

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
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[False] = False,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> _T: ...


@overload
def mutation(
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> Any: ...


@overload
def mutation(
    resolver: Union[StrawberryResolver, Callable, staticmethod, classmethod],
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> DjangoMutationBase: ...


def mutation(
    resolver=None,
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Optional[bool] = None,
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
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[False] = False,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> _T: ...


@overload
def input_mutation(
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> Any: ...


@overload
def input_mutation(
    resolver: Union[StrawberryResolver, Callable, staticmethod, classmethod],
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
) -> DjangoMutationBase: ...


def input_mutation(
    resolver=None,
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    handle_django_errors: Optional[bool] = None,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Optional[bool] = None,
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
    input_type: Optional[type] = None,
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    argument_name: Optional[str] = None,
    handle_django_errors: Optional[bool] = None,
    full_clean: Union[bool, FullCleanOptions] = True,
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
    input_type: Optional[type] = None,
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    filters: Union[type, UnsetType, None] = UNSET,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    graphql_type: Optional[Any] = None,
    extensions: Optional[list[FieldExtension]] = None,
    argument_name: Optional[str] = None,
    handle_django_errors: Optional[bool] = None,
    key_attr: Optional[str] = None,
    full_clean: Union[bool, FullCleanOptions] = True,
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
    input_type: Optional[type] = None,
    *,
    name: Optional[str] = None,
    field_name: Optional[str] = None,
    filters: Union[type, UnsetType, None] = UNSET,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[list[type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    extensions: Optional[list[FieldExtension]] = None,
    graphql_type: Optional[Any] = None,
    argument_name: Optional[str] = None,
    handle_django_errors: Optional[bool] = None,
    key_attr: Optional[str] = None,
    full_clean: Union[bool, FullCleanOptions] = True,
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
