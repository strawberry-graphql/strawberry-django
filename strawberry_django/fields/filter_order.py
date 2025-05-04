from __future__ import annotations

import dataclasses
import inspect
from functools import cached_property
from typing import TYPE_CHECKING, Any, Final, Literal, Optional, overload

from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.exceptions import MissingArgumentsAnnotationsError
from strawberry.types.field import StrawberryField
from strawberry.types.fields.resolver import ReservedName, StrawberryResolver
from typing_extensions import Self

from strawberry_django.exceptions import (
    ForbiddenFieldArgumentError,
    MissingFieldArgumentError,
)
from strawberry_django.utils.typing import is_auto

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping, Sequence

    from strawberry.extensions.field_extension import FieldExtension
    from strawberry.types import Info
    from strawberry.types.field import _RESOLVER_TYPE, T


QUERYSET_PARAMSPEC = ReservedName("queryset")
PREFIX_PARAMSPEC = ReservedName("prefix")
SEQUENCE_PARAMSPEC = ReservedName("sequence")
VALUE_PARAM = ReservedName("value")

OBJECT_FILTER_NAME: Final[str] = "filter"
OBJECT_ORDER_NAME: Final[str] = "order"
WITH_NONE_META: Final[str] = "WITH_NONE_META"
RESOLVE_VALUE_META: Final[str] = "RESOLVE_VALUE_META"


class FilterOrderFieldResolver(StrawberryResolver):
    RESERVED_PARAMSPEC = (
        *StrawberryResolver.RESERVED_PARAMSPEC,
        QUERYSET_PARAMSPEC,
        PREFIX_PARAMSPEC,
        SEQUENCE_PARAMSPEC,
        VALUE_PARAM,
    )

    def __init__(self, *args, resolver_type: Literal["filter", "order"], **kwargs):
        super().__init__(*args, **kwargs)
        self._resolver_type = resolver_type

    def validate_filter_arguments(self):
        is_object_filter = self.name == OBJECT_FILTER_NAME
        is_object_order = self.name == OBJECT_ORDER_NAME

        if not self.reserved_parameters[PREFIX_PARAMSPEC]:
            raise MissingFieldArgumentError(PREFIX_PARAMSPEC.name, self)

        if (is_object_filter or is_object_order) and not self.reserved_parameters[
            QUERYSET_PARAMSPEC
        ]:
            raise MissingFieldArgumentError(QUERYSET_PARAMSPEC.name, self)

        if (
            self._resolver_type != OBJECT_ORDER_NAME
            and self.reserved_parameters[SEQUENCE_PARAMSPEC]
        ):
            raise ForbiddenFieldArgumentError(self, [SEQUENCE_PARAMSPEC.name])

        value_param = self.reserved_parameters[VALUE_PARAM]
        if value_param:
            if is_object_filter or is_object_order:
                raise ForbiddenFieldArgumentError(self, [VALUE_PARAM.name])

            annotation = self.strawberry_annotations[value_param]
            if annotation is None:
                raise MissingArgumentsAnnotationsError(self, [VALUE_PARAM.name])
        elif not is_object_filter and not is_object_order:
            raise MissingFieldArgumentError(VALUE_PARAM.name, self)

        parameters = self.signature.parameters.values()
        reserved_parameters = set(self.reserved_parameters.values())
        exta_params = [p for p in parameters if p not in reserved_parameters]
        if exta_params:
            raise ForbiddenFieldArgumentError(self, [p.name for p in exta_params])

    @cached_property
    def type_annotation(self) -> StrawberryAnnotation | None:
        param = self.reserved_parameters[VALUE_PARAM]
        if param and param is not inspect.Signature.empty:
            annotation = param.annotation
            if is_auto(annotation) and self._resolver_type == OBJECT_ORDER_NAME:
                from strawberry_django import ordering

                annotation = ordering.Ordering

            return StrawberryAnnotation(Optional[annotation])

        return None

    def __call__(  # type: ignore
        self,
        source: Any,
        info: Info | None,
        queryset=None,
        sequence=None,
        **kwargs: Any,
    ) -> Any:
        args = []

        if self.self_parameter:
            args.append(source)

        if parent_parameter := self.parent_parameter:
            kwargs[parent_parameter.name] = source

        if root_parameter := self.root_parameter:
            kwargs[root_parameter.name] = source

        if info_parameter := self.info_parameter:
            assert info is not None
            kwargs[info_parameter.name] = info

        if info_parameter := self.reserved_parameters.get(QUERYSET_PARAMSPEC):
            assert queryset is not None
            kwargs[info_parameter.name] = queryset

        if info_parameter := self.reserved_parameters.get(SEQUENCE_PARAMSPEC):
            assert sequence is not None
            kwargs[info_parameter.name] = sequence

        return super().__call__(*args, **kwargs)


class FilterOrderField(StrawberryField):
    base_resolver: FilterOrderFieldResolver | None  # type: ignore

    def __call__(self, resolver: _RESOLVER_TYPE) -> Self | FilterOrderFieldResolver:  # type: ignore
        if not isinstance(resolver, StrawberryResolver):
            resolver = FilterOrderFieldResolver(
                resolver, resolver_type=self.metadata["_FIELD_TYPE"]
            )
        elif not isinstance(resolver, FilterOrderFieldResolver):
            raise TypeError(
                'Expected resolver to be instance of "FilterOrderFieldResolver", '
                f'found "{type(resolver)}"'
            )

        super().__call__(resolver)
        self._arguments = []
        resolver.validate_filter_arguments()

        if resolver.name in {OBJECT_FILTER_NAME, OBJECT_ORDER_NAME}:
            # For object filter we return resolver
            return resolver

        self.init = self.compare = self.repr = True
        return self


@overload
def filter_field(
    *,
    resolver: _RESOLVER_TYPE[T],
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[False] = False,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    filter_none: bool = False,
    resolve_value: bool = UNSET,
) -> T: ...


@overload
def filter_field(
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    filter_none: bool = False,
    resolve_value: bool = UNSET,
) -> Any: ...


@overload
def filter_field(
    resolver: _RESOLVER_TYPE[T],
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    filter_none: bool = False,
    resolve_value: bool = UNSET,
) -> StrawberryField: ...


def filter_field(
    resolver: _RESOLVER_TYPE[Any] | None = None,
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    filter_none: bool = False,
    resolve_value: bool = UNSET,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
) -> Any:
    """Annotates a method or property as a Django filter field.

    If using with method, these parameters are required: queryset, value, prefix
    Additionaly value has to be annotated with type of filter

    This is normally used inside a type declaration:

    >>> @strawberry_django.filter_type(SomeModel)
    >>> class X:
    >>>     field_abc: strawberry.auto = strawberry_django.filter_field()

    >>>     @strawberry.filter_field(description="ABC")
    >>>     def field_with_resolver(self, queryset, info, value: str, prefix):
    >>>         return

    it can be used both as decorator and as a normal function.
    """
    metadata = metadata or {}
    metadata["_FIELD_TYPE"] = OBJECT_FILTER_NAME
    metadata[RESOLVE_VALUE_META] = resolve_value
    metadata[WITH_NONE_META] = filter_none

    field_ = FilterOrderField(
        python_name=None,
        graphql_name=name,
        is_subscription=is_subscription,
        description=description,
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives,
        extensions=extensions or [],
    )

    if resolver:
        return field_(resolver)

    return field_


@overload
def order_field(
    *,
    resolver: _RESOLVER_TYPE[T],
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[False] = False,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    order_none: bool = False,
) -> T: ...


@overload
def order_field(
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    order_none: bool = False,
) -> Any: ...


@overload
def order_field(
    resolver: _RESOLVER_TYPE[T],
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    order_none: bool = False,
) -> StrawberryField: ...


def order_field(
    resolver: _RESOLVER_TYPE[Any] | None = None,
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    deprecation_reason: str | None = None,
    default: Any = UNSET,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: MutableMapping[Any, Any] | None = None,
    directives: Sequence[object] = (),
    extensions: list[FieldExtension] | None = None,
    order_none: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
) -> Any:
    """Annotates a method or property as a Django filter field.

    If using with method, these parameters are required: queryset, value, prefix
    Additionaly value has to be annotated with type of filter

    This is normally used inside a type declaration:

    >>> @strawberry_django.order(SomeModel)
    >>> class X:
    >>>     field_abc: strawberry.auto = strawberry_django.order_field()

    >>>     @strawberry.order_field(description="ABC")
    >>>     def field_with_resolver(self, queryset, info, value: str, prefix):
    >>>         return

    it can be used both as decorator and as a normal function.
    """
    metadata = metadata or {}
    metadata["_FIELD_TYPE"] = OBJECT_ORDER_NAME
    metadata[WITH_NONE_META] = order_none

    field_ = FilterOrderField(
        python_name=None,
        graphql_name=name,
        is_subscription=is_subscription,
        description=description,
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives,
        extensions=extensions or [],
    )

    if resolver:
        return field_(resolver)

    return field_
