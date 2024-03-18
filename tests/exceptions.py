from strawberry_django.exceptions import (
    ForbiddenFieldArgumentError,
)
from strawberry_django.fields.filter_order import FilterOrderFieldResolver


def test_forbidden_field_argument_extra_one():
    resolver = FilterOrderFieldResolver(resolver_type="filter", func=lambda x: x)

    exc = ForbiddenFieldArgumentError(resolver, ["one"])
    assert exc.extra_arguments_str == 'argument "one"'


def test_forbidden_field_argument_extra_many():
    resolver = FilterOrderFieldResolver(resolver_type="filter", func=lambda x: x)

    exc = ForbiddenFieldArgumentError(resolver, ["extra", "forbidden", "fields"])
    assert exc.extra_arguments_str == 'arguments "extra, forbidden" and "fields"'
