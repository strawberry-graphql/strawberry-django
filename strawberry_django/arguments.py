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
    argument_type = type_
    if is_list:
        argument_type = list[type_]
    if is_optional:
        argument_type = Optional[type_]  # noqa: UP045

    return StrawberryArgument(
        default=default,
        description=None,
        graphql_name=None,
        python_name=name,
        type_annotation=StrawberryAnnotation(argument_type),
    )
