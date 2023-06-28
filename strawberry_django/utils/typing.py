from __future__ import annotations

import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Iterable,
    Sequence,
    TypeVar,
    Union,
    overload,
)

from django.db.models import Prefetch
from graphql.type.definition import GraphQLResolveInfo
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
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from typing_extensions import Literal, TypeAlias, TypeGuard

    from strawberry_django.type import StrawberryDjangoDefinition

_T = TypeVar("_T")
_Type = TypeVar("_Type", bound="StrawberryType | type")

TypeOrSequence: TypeAlias = Union[_T, Sequence[_T]]
TypeOrIterable: TypeAlias = Union[_T, Iterable[_T]]
UserType: TypeAlias = Union["AbstractBaseUser", "AnonymousUser"]
PrefetchCallable: TypeAlias = Callable[[GraphQLResolveInfo], Prefetch]
PrefetchType: TypeAlias = Union[str, Prefetch, PrefetchCallable]


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


def is_auto(obj: Any) -> bool:
    if isinstance(obj, str):
        return obj in ["auto", "strawberry.auto"]

    return isinstance(obj, StrawberryAuto)


def get_annotations(cls) -> dict[str, StrawberryAnnotation]:
    annotations: dict[str, StrawberryAnnotation] = {}

    for c in reversed(cls.__mro__):
        namespace = sys.modules[c.__module__].__dict__
        for k, v in getattr(c, "__annotations__", {}).items():
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
