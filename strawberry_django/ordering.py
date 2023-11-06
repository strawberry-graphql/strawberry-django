import dataclasses
import enum
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

import strawberry
from django.db import models
from graphql.language.ast import ObjectValueNode
from strawberry import UNSET
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField, field
from strawberry.type import WithStrawberryObjectDefinition, has_object_definition
from strawberry.types import Info
from strawberry.unset import UnsetType
from typing_extensions import Self, dataclass_transform

from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.utils.typing import is_auto

from .arguments import argument

if TYPE_CHECKING:
    from django.db.models import QuerySet


_T = TypeVar("_T")
_QS = TypeVar("_QS", bound="QuerySet")

ORDER_ARG = "order"


@dataclasses.dataclass
class _OrderSequence:
    seq: int = 0
    children: Optional[Dict[str, "_OrderSequence"]] = None


@strawberry.enum
class Ordering(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


def generate_order_args(
    order: WithStrawberryObjectDefinition,
    *,
    sequence: Optional[Dict[str, _OrderSequence]] = None,
    prefix: str = "",
):
    sequence = sequence or {}
    args = []

    def sort_key(f: StrawberryField) -> int:
        if not (seq := sequence.get(f.name)):
            return 0
        return seq.seq

    for f in sorted(order.__strawberry_definition__.fields, key=sort_key):
        ordering = getattr(order, f.name, UNSET)
        if ordering is UNSET:
            continue

        if ordering == Ordering.ASC:
            args.append(f"{prefix}{f.name}")
        elif ordering == Ordering.DESC:
            args.append(f"-{prefix}{f.name}")
        else:
            subargs = generate_order_args(
                ordering,
                prefix=f"{prefix}{f.name}__",
                sequence=(seq := sequence.get(f.name)) and seq.children,
            )
            args.extend(subargs)

    return args


def apply(
    order: Optional[WithStrawberryObjectDefinition],
    queryset: _QS,
    info: Optional[Info] = None,
) -> _QS:
    if order in (None, strawberry.UNSET):  # noqa: PLR6201
        return queryset

    sequence: Dict[str, _OrderSequence] = {}
    if info is not None and info._raw_info.field_nodes:
        field_node = info._raw_info.field_nodes[0]
        for arg in field_node.arguments:
            if arg.name.value != ORDER_ARG or not isinstance(
                arg.value, ObjectValueNode
            ):
                continue

            def parse_and_fill(field: ObjectValueNode, seq: Dict[str, _OrderSequence]):
                for i, f in enumerate(field.fields):
                    f_sequence: Dict[str, _OrderSequence] = {}
                    if isinstance(f.value, ObjectValueNode):
                        parse_and_fill(f.value, f_sequence)

                    seq[f.name.value] = _OrderSequence(seq=i, children=f_sequence)

            parse_and_fill(arg.value, sequence)

    args = generate_order_args(order, sequence=sequence)
    if not args:
        return queryset
    return queryset.order_by(*args)


class StrawberryDjangoFieldOrdering(StrawberryDjangoFieldBase):
    def __init__(self, order: Union[type, UnsetType, None] = UNSET, **kwargs):
        if order and not has_object_definition(order):
            raise TypeError("order needs to be a strawberry type")

        self.order = order
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.order = self.order
        return new_field

    @property
    def arguments(self) -> List[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and self.is_list:
            order = self.get_order()
            if order and order is not UNSET:
                arguments.append(argument("order", order, is_optional=True))
        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: List[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldOrdering, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_order(self) -> Optional[Type[WithStrawberryObjectDefinition]]:
        order = self.order
        if order is None:
            return None

        if isinstance(order, UnsetType):
            django_type = self.django_type
            order = (
                django_type.__strawberry_django_definition__.order
                if django_type is not None
                else None
            )

        return order if order is not UNSET else None

    def apply_order(
        self,
        queryset: _QS,
        order: Optional[WithStrawberryObjectDefinition] = None,
        info: Optional[Info] = None,
    ) -> _QS:
        return apply(order, queryset, info=info)

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        order: Optional[WithStrawberryObjectDefinition] = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return self.apply_order(queryset, order, info=info)


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        field,
    ),
)
def order(
    model: Type[models.Model],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
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
