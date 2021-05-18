import enum
import strawberry
import strawberry_django
from strawberry.arguments import UNSET, is_unset, StrawberryArgument
from typing import Optional, List

from .arguments import argument
from . import utils


@strawberry.enum
class Ordering(enum.Enum):
    ASC = 'ASC'
    DESC = 'DESC'


def generate_order_args(order, prefix=''):
    args = []
    for field in strawberry_django.fields(order):
        ordering = getattr(order, field.name, utils.UNSET)
        if utils.is_unset(ordering):
            continue
        if ordering == Ordering.ASC:
            args.append(f'{prefix}{field.name}')
        elif ordering == Ordering.DESC:
            args.append(f'-{prefix}{field.name}')
        else:
            prefix = f'{prefix}{field.name}__'
            subargs = generate_order_args(ordering, prefix=prefix)
            args.extend(subargs)
    return args

def order(model):
    def wrapper(cls):
        for name, type_ in cls.__annotations__.items():
            if strawberry_django.is_auto(type_):
                type_ = Ordering
            cls.__annotations__[name] = Optional[type_]
            setattr(cls, name, utils.UNSET)
        return strawberry.input(cls)
    return wrapper


def apply(order, queryset):
    if utils.is_unset(order) or order is None:
        return queryset
    args = generate_order_args(order)
    if not args:
        return queryset
    return queryset.order_by(*args)


class StrawberryDjangoFieldOrdering:
    def __init__(self, order=None, **kwargs):
        self.order = order
        super().__init__(**kwargs)

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if not self.base_resolver:
            if self.order:
                arguments.append(
                    argument('order', self.order)
                )
        return super().arguments + arguments

    def get_queryset(self, queryset, info, order=UNSET, **kwargs):
        queryset = apply(order, queryset)
        return super().get_queryset(queryset, info, **kwargs)
