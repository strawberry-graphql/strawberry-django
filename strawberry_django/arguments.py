from typing import Optional

from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.arguments import StrawberryArgument


def argument(
    name: str,
    type_: type,
    *,
    is_list: bool = False,
    is_optional: bool = False,
    default: object = UNSET,
):
    if is_list:
        type_ = list[type_]
    if is_optional:
        type_ = Optional[type_]

    return StrawberryArgument(
        default=default,
        description=None,
        graphql_name=None,
        python_name=name,
        type_annotation=StrawberryAnnotation(type_),
    )
