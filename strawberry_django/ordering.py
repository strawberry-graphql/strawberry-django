from __future__ import annotations

import dataclasses
import enum
from typing import (
    TYPE_CHECKING,
    Callable,
    Collection,
    Optional,
    Sequence,
    TypeVar,
    cast,
)

import strawberry
from django.db.models import F, OrderBy, QuerySet
from graphql.language.ast import ObjectValueNode
from strawberry import UNSET
from strawberry.types import has_object_definition
from strawberry.types.base import WithStrawberryObjectDefinition
from strawberry.types.field import StrawberryField, field
from strawberry.types.unset import UnsetType
from strawberry.utils.str_converters import to_camel_case
from typing_extensions import Self, dataclass_transform

from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.fields.filter_order import (
    WITH_NONE_META,
    FilterOrderField,
    FilterOrderFieldResolver,
)
from strawberry_django.utils.typing import is_auto

from .arguments import argument

if TYPE_CHECKING:
    from django.db.models import Model
    from strawberry.types import Info
    from strawberry.types.arguments import StrawberryArgument

_T = TypeVar("_T")
_QS = TypeVar("_QS", bound="QuerySet")
_SFT = TypeVar("_SFT", bound=StrawberryField)

ORDER_ARG = "order"


@dataclasses.dataclass
class OrderSequence:
    seq: int = 0
    children: dict[str, OrderSequence] | None = None

    @classmethod
    def get_graphql_name(cls, info: Info | None, field: StrawberryField) -> str:
        if info is None:
            if field.graphql_name:
                return field.graphql_name

            return to_camel_case(field.python_name)

        return info.schema.config.name_converter.get_graphql_name(field)

    @classmethod
    def sorted(
        cls,
        info: Info | None,
        sequence: dict[str, OrderSequence] | None,
        fields: list[_SFT],
    ) -> list[_SFT]:
        if info is None:
            return fields

        sequence = sequence or {}

        def sort_key(f: _SFT) -> int:
            if not (seq := sequence.get(cls.get_graphql_name(info, f))):
                return 0
            return seq.seq

        return sorted(fields, key=sort_key)


@strawberry.enum
class Ordering(enum.Enum):
    ASC = "ASC"
    ASC_NULLS_FIRST = "ASC_NULLS_FIRST"
    ASC_NULLS_LAST = "ASC_NULLS_LAST"
    DESC = "DESC"
    DESC_NULLS_FIRST = "DESC_NULLS_FIRST"
    DESC_NULLS_LAST = "DESC_NULLS_LAST"

    def resolve(self, value: str) -> OrderBy:
        nulls_first = True if "NULLS_FIRST" in self.name else None
        nulls_last = True if "NULLS_LAST" in self.name else None
        if "ASC" in self.name:
            return F(value).asc(nulls_first=nulls_first, nulls_last=nulls_last)
        return F(value).desc(nulls_first=nulls_first, nulls_last=nulls_last)


def process_order(
    order: WithStrawberryObjectDefinition,
    info: Info | None,
    queryset: _QS,
    *,
    sequence: dict[str, OrderSequence] | None = None,
    prefix: str = "",
    skip_object_order_method: bool = False,
) -> tuple[_QS, Collection[F | OrderBy | str]]:
    sequence = sequence or {}
    args = []

    if not skip_object_order_method and isinstance(
        order_method := getattr(order, "order", None),
        FilterOrderFieldResolver,
    ):
        return order_method(
            order, info, queryset=queryset, prefix=prefix, sequence=sequence
        )

    for f in OrderSequence.sorted(
        info, sequence, order.__strawberry_definition__.fields
    ):
        f_value = getattr(order, f.name, UNSET)
        if f_value is UNSET or (f_value is None and not f.metadata.get(WITH_NONE_META)):
            continue

        if isinstance(f, FilterOrderField) and f.base_resolver:
            res = f.base_resolver(
                order,
                info,
                value=f_value,
                queryset=queryset,
                prefix=prefix,
                sequence=(
                    (seq := sequence.get(OrderSequence.get_graphql_name(info, f)))
                    and seq.children
                ),
            )
            if isinstance(res, tuple):
                queryset, subargs = res
            else:
                subargs = res
            args.extend(subargs)
        elif isinstance(f_value, Ordering):
            args.append(f_value.resolve(f"{prefix}{f.name}"))
        else:
            queryset, subargs = process_order(
                f_value,
                info,
                queryset,
                prefix=f"{prefix}{f.name}__",
                sequence=(
                    (seq := sequence.get(OrderSequence.get_graphql_name(info, f)))
                    and seq.children
                ),
            )
            args.extend(subargs)

    return queryset, args


def apply(
    order: object | None,
    queryset: _QS,
    info: Info | None = None,
) -> _QS:
    if order in (None, strawberry.UNSET) or not has_object_definition(order):  # noqa: PLR6201
        return queryset

    sequence: dict[str, OrderSequence] = {}
    if info is not None and info._raw_info.field_nodes:
        field_node = info._raw_info.field_nodes[0]
        for arg in field_node.arguments:
            if arg.name.value != ORDER_ARG or not isinstance(
                arg.value, ObjectValueNode
            ):
                continue

            def parse_and_fill(field: ObjectValueNode, seq: dict[str, OrderSequence]):
                for i, f in enumerate(field.fields):
                    f_sequence: dict[str, OrderSequence] = {}
                    if isinstance(f.value, ObjectValueNode):
                        parse_and_fill(f.value, f_sequence)

                    seq[f.name.value] = OrderSequence(seq=i, children=f_sequence)

            parse_and_fill(arg.value, sequence)

    queryset, args = process_order(
        cast(WithStrawberryObjectDefinition, order), info, queryset, sequence=sequence
    )
    if not args:
        return queryset
    return queryset.order_by(*args)


class StrawberryDjangoFieldOrdering(StrawberryDjangoFieldBase):
    def __init__(self, order: type | UnsetType | None = UNSET, **kwargs):
        if order and not has_object_definition(order):
            raise TypeError("order needs to be a strawberry type")

        self.order = order
        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.order = self.order
        return new_field

    @property
    def arguments(self) -> list[StrawberryArgument]:
        arguments = []
        if self.base_resolver is None and self.is_list:
            order = self.get_order()
            if order and order is not UNSET:
                arguments.append(argument("order", order, is_optional=True))
        return super().arguments + arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(StrawberryDjangoFieldOrdering, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def get_order(self) -> type[WithStrawberryObjectDefinition] | None:
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

    def get_queryset(
        self,
        queryset: _QS,
        info: Info,
        *,
        order: WithStrawberryObjectDefinition | None = None,
        **kwargs,
    ) -> _QS:
        queryset = super().get_queryset(queryset, info, **kwargs)
        return apply(order, queryset, info=info)


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        field,
    ),
)
def order(
    model: type[Model],
    *,
    name: str | None = None,
    description: str | None = None,
    directives: Sequence[object] | None = (),
) -> Callable[[_T], _T]:
    def wrapper(cls):
        try:
            cls.__annotations__  # noqa: B018
        except AttributeError:
            # Manual creation for python 3.8 / 3.9
            cls.__annotations__ = {}

        for fname, type_ in cls.__annotations__.items():
            if is_auto(type_):
                type_ = Ordering  # noqa: PLW2901

            cls.__annotations__[fname] = Optional[type_]

            field_ = cls.__dict__.get(fname)
            if not isinstance(field_, StrawberryField):
                setattr(cls, fname, UNSET)

        return strawberry.input(
            cls,
            name=name,
            description=description,
            directives=directives,
        )

    return wrapper
