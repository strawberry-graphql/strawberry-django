from strawberry.arguments import StrawberryArgument
from strawberry.types.types import undefined

def argument(name, type_, is_optional=True, default_value=undefined):
    return StrawberryArgument(
        default_value=default_value,
        description=None,
        graphql_name=None,
        is_optional=is_optional,
        origin=None,
        python_name=name,
        type_=type_,
    )

