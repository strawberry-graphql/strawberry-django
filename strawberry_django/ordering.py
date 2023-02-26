from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Optional

import strawberry
from strawberry import UNSET
from strawberry.auto import StrawberryAuto

from strawberry_django.utils import fields

from . import utils
from .arguments import argument

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from strawberry.arguments import StrawberryArgument
    from strawberry.types import Info


@strawberry.enum
class Ordering(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


def generate_order_args(order, prefix=""):
    args = []
    for field in fields(order):
        ordering = getattr(order, field.name, UNSET)
        if ordering is UNSET:
            continue
        if ordering == Ordering.ASC:
            args.append(f"{prefix}{field.name}")
        elif ordering == Ordering.DESC:
            args.append(f"-{prefix}{field.name}")
        else:
            subargs = generate_order_args(ordering, prefix=f"{prefix}{field.name}__")
            args.extend(subargs)
    return args


def order(model):
    def wrapper(cls):
        for name, type_ in cls.__annotations__.items():
            cls.__annotations__[name] = Optional[
                Ordering if isinstance(type_, StrawberryAuto) else type_
            ]
            setattr(cls, name, UNSET)
        return strawberry.input(cls)

    return wrapper


def apply(order, queryset: QuerySet) -> QuerySet:
    if order is UNSET or order is None:
        return queryset
    args = generate_order_args(order)
    if not args:
        return queryset
    return queryset.order_by(*args)


class StrawberryDjangoFieldOrdering:
    def __init__(self, order=UNSET, **kwargs):
        self.order = order
        super().__init__(**kwargs)

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if not self.base_resolver:
            order = self.get_order()
            if order and order is not UNSET and self.is_list:
                arguments.append(argument("order", order))
        return super().arguments + arguments

    def get_order(self) -> type | None:
        if self.order is not UNSET:
            return self.order
        type_ = utils.unwrap_type(self.type or self.child.type)

        if utils.is_django_type(type_):
            return type_._django_type.order
        return None

    def apply_order(self, queryset: QuerySet, order) -> QuerySet:
        return apply(order, queryset)

    def get_queryset(
        self,
        queryset: QuerySet,
        info: Info,
        order: type = UNSET,
        **kwargs,
    ):
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_order(queryset, order)
