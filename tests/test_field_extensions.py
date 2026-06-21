import strawberry
from strawberry.annotation import StrawberryAnnotation
from strawberry.extensions.field_extension import FieldExtension
from strawberry.types.arguments import StrawberryArgument

import strawberry_django
from tests.models import Fruit


class AddArgumentExtension(FieldExtension):
    def apply(self, field):
        field.arguments.append(
            StrawberryArgument(
                python_name="some_argument",
                graphql_name="someArgument",
                type_annotation=StrawberryAnnotation(annotation=bool | None),
            ),
        )

    def resolve(self, next_, source, info, **kwargs):
        return next_(source, info, **kwargs)


def test_field_extension_arguments_on_strawberry_django_field():
    @strawberry.type
    class Query:
        @strawberry_django.field(extensions=[AddArgumentExtension()])
        def my_field(self) -> bool:
            return True

    schema = strawberry.Schema(query=Query)
    schema_str = schema.as_str()
    assert "someArgument" in schema_str


def test_field_extension_arguments_on_strawberry_django_field_list():
    @strawberry_django.type(Fruit)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field(extensions=[AddArgumentExtension()])
        def my_field(self) -> list[FruitType]:
            return []

    schema = strawberry.Schema(query=Query)
    schema_str = schema.as_str()
    assert "someArgument" in schema_str


def test_field_extension_arguments_parity_with_strawberry_field():
    @strawberry.type
    class Query:
        @strawberry.field(extensions=[AddArgumentExtension()])
        def strawberry_field(self) -> bool:
            return True

        @strawberry_django.field(extensions=[AddArgumentExtension()])
        def django_field(self) -> bool:
            return True

    schema = strawberry.Schema(query=Query)
    schema_str = schema.as_str()

    for line in schema_str.split("\n"):
        if "strawberryField" in line:
            assert "someArgument" in line
        if "djangoField" in line:
            assert "someArgument" in line
