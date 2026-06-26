import dataclasses
import textwrap

import pytest
import strawberry
from django.db import models
from strawberry.exceptions.duplicated_type_name import DuplicatedTypeName
from strawberry.types import get_object_definition

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.utils.typing import get_django_definition
from tests import models as test_models


def _supports_graphql_type_extension() -> bool:
    """Whether the installed Strawberry core can emit same-name `extend` types.

    The `extend=True` support on `strawberry_django.type`/`input`/`partial`
    relies on Strawberry core emitting a separate `extend type X` block next to
    the base `type X` in the same schema. Stock Strawberry instead rejects two
    same-named definitions with `DuplicatedTypeName`. Probe once so the
    dependent tests skip cleanly on releases without that support.
    """

    @strawberry.type(name="_ExtensionProbe")
    class _ProbeBase:
        base: str

    @strawberry.type(name="_ExtensionProbe", extend=True)
    class _ProbeExtension:
        extra: str

    @strawberry.type
    class _ProbeQuery:
        probe: _ProbeBase

    try:
        strawberry.Schema(query=_ProbeQuery, types=[_ProbeExtension])
    except DuplicatedTypeName:
        return False
    return True


requires_graphql_type_extension = pytest.mark.skipif(
    not _supports_graphql_type_extension(),
    reason=(
        "requires Strawberry core support for same-name `extend` types "
        "(not available in the pinned strawberry release)"
    ),
)


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
    class SomeModel2(models.Model):
        name = models.CharField(max_length=255)

    class NonDataclass:
        non_dataclass_attr: str

    @dataclasses.dataclass
    class SomeDataclass:
        some_dataclass_attr: str

    @strawberry.input
    class SomeStrawberryInput:
        some_strawberry_attr: str

    @strawberry_django.input(SomeModel2)
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


@requires_graphql_type_extension
def test_input_can_extend_existing_input_type():
    @strawberry_django.input(test_models.User, name="UserInput", fields=["name"])
    class UserInput: ...

    @strawberry_django.input(test_models.User, name="UserInput", extend=True)
    class UserInputExtension:
        extra: str

    @strawberry.type
    class Query:
        @strawberry.field
        def some_field(self, my_input: UserInput) -> str:
            return f"{my_input.name} {my_input.extra}"  # pyright: ignore[reportAttributeAccessIssue]

    schema = strawberry.Schema(query=Query, types=[UserInputExtension])
    expected = """\
    type Query {
      someField(myInput: UserInput!): String!
    }

    input UserInput {
      name: String!
    }

    extend input UserInput {
      extra: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        '{ someField(myInput: { name: "Ada", extra: "Lovelace" }) }'
    )

    assert result.errors is None
    assert result.data == {"someField": "Ada Lovelace"}


def test_partial_can_extend_existing_input_type():
    @strawberry_django.partial(test_models.User, name="UserInput", extend=True)
    class UserInputExtension:
        extra: str | None

    type_def = get_object_definition(UserInputExtension, strict=True)
    assert type_def.extend is True


@requires_graphql_type_extension
def test_type_can_extend_existing_type():
    @strawberry_django.type(test_models.User, name="UserType", fields=["name"])
    class UserType: ...

    @strawberry_django.type(test_models.User, name="UserType", extend=True)
    class UserTypeExtension:
        @strawberry.field
        def extra(self) -> str:
            return self.extra  # pyright: ignore[reportReturnType]

    @strawberry.type
    class Query:
        @strawberry.field
        def user(self) -> UserType:
            user = test_models.User(name="Ada")
            user.extra = "Lovelace"  # pyright: ignore[reportAttributeAccessIssue]
            return user  # pyright: ignore[reportReturnType]

    schema = strawberry.Schema(query=Query, types=[UserTypeExtension])
    expected = """\
    type Query {
      user: UserType!
    }

    type UserType {
      name: String!
    }

    extend type UserType {
      extra: String!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync("{ user { name extra } }")

    assert result.errors is None
    assert result.data == {"user": {"name": "Ada", "extra": "Lovelace"}}


def test_optimizer_hints_on_type():
    class OtherModel(models.Model):
        name = models.CharField(max_length=255)

    class SomeModel3(models.Model):
        name = models.CharField(max_length=255)
        other = models.ForeignKey(OtherModel, on_delete=models.CASCADE)

    @strawberry_django.type(
        SomeModel3,
        only=["name", "other", "other_name"],
        select_related=["other"],
        prefetch_related=["other"],
        annotate={"other_name": models.F("other__name")},
    )
    class SomeModelType:
        name: str

    store = get_django_definition(SomeModelType, strict=True).store

    assert store.only == ["name", "other", "other_name"]
    assert store.select_related == ["other"]
    assert store.prefetch_related == ["other"]
    assert store.annotate == {"other_name": models.F("other__name")}


def test_custom_field_kept_on_inheritance():
    class SomeModel4(models.Model):
        foo = models.CharField(max_length=255)

    class CustomField(StrawberryDjangoField): ...

    @strawberry_django.type(SomeModel4)
    class SomeModelType:
        foo: strawberry.auto = CustomField()

    @strawberry_django.type(SomeModel4)
    class SomeModelSubclassType(SomeModelType): ...

    for type_ in [SomeModelType, SomeModelSubclassType]:
        object_definition = get_object_definition(type_, strict=True)
        field = object_definition.get_field("foo")
        assert isinstance(field, CustomField)
