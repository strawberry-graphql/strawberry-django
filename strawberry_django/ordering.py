from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Sequence, TypeVar

import strawberry
from strawberry import UNSET
from strawberry.field import StrawberryField, field
from strawberry.unset import UnsetType
from typing_extensions import Self, dataclass_transform

from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.utils import (
    WithStrawberryObjectDefinition,
    fields,
    is_auto,
    is_strawberry_type,
)

from . import utils
from .arguments import argument

if TYPE_CHECKING:
    from django.db import models
    from django.db.models import QuerySet
    from strawberry.arguments import StrawberryArgument
    from strawberry.type import StrawberryType
    from strawberry.types import Info


_T = TypeVar("_T")
_QS = TypeVar("_QS", bound="QuerySet")


@strawberry.enum
class Ordering(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


def generate_order_args(order: WithStrawberryObjectDefinition, prefix: str = ""):
    args = []
    for f in fields(order):
        ordering = getattr(order, f.name, UNSET)
        if ordering is UNSET:
            continue

        if ordering == Ordering.ASC:
            args.append(f"{prefix}{f.name}")
        elif ordering == Ordering.DESC:
            args.append(f"-{prefix}{f.name}")
        else:
            subargs = generate_order_args(ordering, prefix=f"{prefix}{f.name}__")
            args.extend(subargs)

    return args


def apply(order: WithStrawberryObjectDefinition | None, queryset: _QS) -> _QS:
    if order in (None, strawberry.UNSET):
        return queryset

    args = generate_order_args(order)
    if not args:
        return queryset
    return queryset.order_by(*args)


class StrawberryDjangoFieldOrdering(StrawberryDjangoFieldBase):
    def __init__(self, order: type | UnsetType | None = UNSET, **kwargs):
        if order and not is_strawberry_type(order):
            raise TypeError("order needs to be a strawberry type")

        self.order = order
        super().__init__(**kwargs)

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and self.is_list:
            order = self.get_order()
            if order and order is not UNSET and self.is_list:
                arguments.append(argument("order", order, is_optional=True))
        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldOrdering, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def copy_with(
        self,
        type_var_map: Mapping[TypeVar, StrawberryType | type],
    ) -> Self:
        new_field = super().copy_with(type_var_map)
        new_field.order = self.order
        return new_field

    def get_order(self) -> type[WithStrawberryObjectDefinition] | None:
        order = self.order
        if order is None:
            return None

        if isinstance(order, UnsetType):
            type_ = utils.unwrap_type(self.type)
            order = type_._django_type.order if utils.is_django_type(type_) else None

        return order

    def apply_order(
        self,
        queryset: _QS,
        order: WithStrawberryObjectDefinition | None = None,
    ) -> _QS:
        return apply(order, queryset)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        order: WithStrawberryObjectDefinition | None = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_order(queryset, order)


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        field,
    ),
)
def order(
    model: type[models.Model],
    *,
    name: str | None = None,
    description: str | None = None,
    directives: Sequence[object] | None = (),
) -> Callable[[_T], _T]:
    def wrapper(cls):
        for fname, type_ in cls.__annotations__.items():
            if is_auto(type_):
                type_ = Ordering  # noqa: PLW2901

            cls.__annotations__[fname] = Optional[type_]
            setattr(cls, fname, UNSET)

        return strawberry.input(
            cls,
            name=name,
            description=description,
            directives=directives,
        )

    return wrapper
