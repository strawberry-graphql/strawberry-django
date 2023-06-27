from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, overload

from strawberry.annotation import StrawberryAnnotation
from strawberry.auto import StrawberryAuto
from strawberry.type import (
    StrawberryContainer,
    StrawberryType,
    WithStrawberryObjectDefinition,
)
from strawberry.utils.typing import is_classvar
from typing_extensions import Protocol

if TYPE_CHECKING:
    from strawberry.field import StrawberryField
    from typing_extensions import Literal, TypeGuard

    from strawberry_django.type import StrawberryDjangoDefinition

_Type = TypeVar("_Type", bound="StrawberryType | type")


class WithStrawberryDjangoObjectDefinition(WithStrawberryObjectDefinition, Protocol):
    __strawberry_django_definition__: ClassVar[StrawberryDjangoDefinition]


def has_django_definition(
    obj: Any,
) -> TypeGuard[type[WithStrawberryDjangoObjectDefinition]]:
    return hasattr(obj, "__strawberry_django_definition__")


@overload
def get_django_definition(
    obj: Any,
    *,
    strict: Literal[True],
) -> StrawberryDjangoDefinition:
    ...


@overload
def get_django_definition(
    obj: Any,
    *,
    strict: bool = False,
) -> StrawberryDjangoDefinition | None:
    ...


def get_django_definition(
    obj: Any,
    *,
    strict: bool = False,
) -> StrawberryDjangoDefinition | None:
    return (
        obj.__strawberry_django_definition__
        if strict
        else getattr(obj, "__strawberry_django_definition__", None)
    )


def is_auto(obj: Any) -> TypeGuard[StrawberryAuto]:
    if isinstance(obj, str):
        # Support future references
        return obj in ["auto", "strawberry.auto"]

    return isinstance(obj, StrawberryAuto)


def fields(obj: WithStrawberryObjectDefinition) -> list[StrawberryField]:
    return obj.__strawberry_definition__.fields


def get_annotations(cls):
    annotations: dict[str, StrawberryAnnotation] = {}

    for c in reversed(cls.__mro__):
        namespace = sys.modules[c.__module__].__dict__
        if "__annotations__" not in c.__dict__:
            continue

        for k, v in c.__annotations__.items():
            if not is_classvar(c, v):
                annotations[k] = StrawberryAnnotation(v, namespace=namespace)

    return annotations


@overload
def unwrap_type(type_: StrawberryContainer) -> StrawberryType | type:
    ...


@overload
def unwrap_type(type_: _Type) -> _Type:
    ...


def unwrap_type(type_):
    while isinstance(type_, StrawberryContainer):
        type_ = type_.of_type

    return type_
