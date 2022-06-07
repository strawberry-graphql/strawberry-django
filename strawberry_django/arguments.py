from typing import Optional

from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument


def argument(name, type_, is_optional=True, default=UNSET):
    if is_optional:
        type_ = Optional[type_]
    return StrawberryArgument(
        default=default,
        description=None,
        graphql_name=None,
        python_name=name,
        type_annotation=StrawberryAnnotation(type_),
    )
