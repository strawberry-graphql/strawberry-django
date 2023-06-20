from __future__ import annotations

import dataclasses
import sys
import typing
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, TypeVar, overload

from strawberry.annotation import StrawberryAnnotation
from strawberry.auto import StrawberryAuto
from strawberry.type import StrawberryContainer, StrawberryType

if TYPE_CHECKING:
    from strawberry.field import StrawberryField
    from strawberry.object_type import TypeDefinition
    from typing_extensions import TypeGuard

    from strawberry_django.type import StrawberryDjangoType

_Type = TypeVar("_Type", bound="StrawberryType | type")


# FIXME: Replace this with strawberry's one once this PR gets merged:
# https://github.com/strawberry-graphql/strawberry/pull/2836
class WithStrawberryObjectDefinition(Protocol):
    _type_definition: ClassVar[TypeDefinition]


class WithStrawberryDjangoObjectDefinition(WithStrawberryObjectDefinition, Protocol):
    _django_type: ClassVar[StrawberryDjangoType]


def is_strawberry_type(obj: Any) -> TypeGuard[type[WithStrawberryObjectDefinition]]:
    return hasattr(obj, "_type_definition")


def is_django_type(obj: Any) -> TypeGuard[type[WithStrawberryDjangoObjectDefinition]]:
    return hasattr(obj, "_django_type")


def is_auto(obj: Any) -> TypeGuard[StrawberryAuto]:
    if isinstance(obj, str):
        # Support future references
        return obj in ["auto", "strawberry.auto"]

    return isinstance(obj, StrawberryAuto)


def fields(obj: WithStrawberryObjectDefinition) -> list[StrawberryField]:
    return obj._type_definition.fields


def get_annotations(cls):
    annotations: dict[str, StrawberryAnnotation] = {}

    for c in reversed(cls.__mro__):
        namespace = sys.modules[c.__module__].__dict__
        if "__annotations__" not in c.__dict__:
            continue

        for k, v in c.__annotations__.items():
            # This is the same check that dataclasses does to
            # exclude classvars from annotations
            is_classvar = dataclasses._is_classvar(v, typing) or (  # type: ignore
                isinstance(v, str)
                and dataclasses._is_type(  # type: ignore
                    v,
                    cls,
                    typing,
                    typing.ClassVar,
                    dataclasses._is_classvar,  # type: ignore
                )
            )
            if not is_classvar:
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
