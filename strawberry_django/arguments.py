from strawberry.arguments import StrawberryArgument, UNSET

def argument(name, type_, is_optional=True, default=UNSET):
    return StrawberryArgument(
        default=default,
        description=None,
        graphql_name=None,
        is_optional=is_optional,
        origin=None,
        python_name=name,
        type_=type_,
    )

