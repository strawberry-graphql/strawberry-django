import dataclasses
import textwrap

import strawberry
from django.db import models

import strawberry_django


def test_non_dataclass_annotations_are_ignored_on_type():
    class SomeModel(models.Model):
        name = models.CharField(max_length=255)

    class NonDataclass:
        non_dataclass_attr: str

    @dataclasses.dataclass
    class SomeDataclass:
        some_dataclass_attr: str

    @strawberry.type
    class SomeStrawberryType:
        some_strawberry_attr: str

    @strawberry_django.type(SomeModel)
    class SomeModelType(SomeStrawberryType, SomeDataclass, NonDataclass):
        name: str

    @strawberry.type
    class Query:
        my_type: SomeModelType

    schema = strawberry.Schema(query=Query)
    expected = """\
    type Query {
      myType: SomeModelType!
    }

    type SomeModelType {
      someStrawberryAttr: String!
      someDataclassAttr: String!
      name: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


def test_non_dataclass_annotations_are_ignored_on_input():
    class SomeModel(models.Model):
        name = models.CharField(max_length=255)

    class NonDataclass:
        non_dataclass_attr: str

    @dataclasses.dataclass
    class SomeDataclass:
        some_dataclass_attr: str

    @strawberry.input
    class SomeStrawberryInput:
        some_strawberry_attr: str

    @strawberry_django.input(SomeModel)
    class SomeModelInput(SomeStrawberryInput, SomeDataclass, NonDataclass):
        name: str

    @strawberry.type
    class Query:
        @strawberry.field
        def some_field(self, my_input: SomeModelInput) -> str: ...

    schema = strawberry.Schema(query=Query)
    expected = """\
    type Query {
      someField(myInput: SomeModelInput!): String!
    }

    input SomeModelInput {
      someStrawberryAttr: String!
      someDataclassAttr: String!
      name: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()
