import pytest
import strawberry
from django.test import override_settings
from strawberry import auto
from strawberry.object_type import StrawberryObjectDefinition
from strawberry.type import get_object_definition

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField
from strawberry_django.settings import StrawberryDjangoSettings

from .models import Book as BookModel
from .models import Color, Fruit, User


def test_type_instance():
    @strawberry_django.type(User)
    class UserType:
        id: auto
        name: auto

    user = UserType(id=1, name="user")
    assert user.id == 1
    assert user.name == "user"


def test_type_instance_auto_as_str():
    @strawberry_django.type(User)
    class UserType:
        id: "auto"
        name: "auto"

    user = UserType(id=1, name="user")
    assert user.id == 1
    assert user.name == "user"


def test_input_instance():
    @strawberry_django.input(User)
    class InputType:
        id: auto
        name: auto

    user = InputType(id=1, name="user")
    assert user.id == 1
    assert user.name == "user"


def test_custom_field_cls():
    """Custom field_cls is applied to all fields."""

    class CustomStrawberryDjangoField(StrawberryDjangoField):
        pass

    @strawberry_django.type(User, field_cls=CustomStrawberryDjangoField)
    class UserType:
        id: int
        name: auto

    assert all(
        isinstance(field, CustomStrawberryDjangoField)
        for field in get_object_definition(UserType, strict=True).fields
    )


def test_custom_field_cls__explicit_field_type():
    """Custom field_cls is applied to all fields."""

    class CustomStrawberryDjangoField(StrawberryDjangoField):
        pass

    @strawberry_django.type(User, field_cls=CustomStrawberryDjangoField)
    class UserType:
        id: int
        name: auto = strawberry_django.field()

    assert isinstance(
        get_object_definition(UserType, strict=True).get_field("id"),
        CustomStrawberryDjangoField,
    )
    assert isinstance(
        get_object_definition(UserType, strict=True).get_field("name"),
        StrawberryDjangoField,
    )
    assert not isinstance(
        get_object_definition(UserType, strict=True).get_field("name"),
        CustomStrawberryDjangoField,
    )


def test_field_metadata_default():
    """Test metadata default.

    Test that textual metadata from the Django model isn't reflected in the Strawberry
    type by default.
    """

    @strawberry_django.type(BookModel)
    class Book:
        title: auto

    type_def = get_object_definition(Book, strict=True)
    assert type_def.description is None
    title_field = type_def.get_field("title")
    assert title_field is not None
    assert title_field.description is None


@override_settings(
    STRAWBERRY_DJANGO=StrawberryDjangoSettings(
        FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
        TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
    ),
)
def test_field_metadata_preserved():
    """Test metadata preserved.

    Test that textual metadata from the Django model is reflected in the Strawberry type
    if the settings are enabled.
    """

    @strawberry_django.type(BookModel)
    class Book:
        title: auto

    type_def = get_object_definition(Book, strict=True)
    assert type_def.description == BookModel.__doc__
    title_field = type_def.get_field("title")
    assert title_field is not None
    assert title_field.description == BookModel._meta.get_field("title").help_text
    assert get_object_definition(Book, strict=True).description == BookModel.__doc__


@override_settings(
    STRAWBERRY_DJANGO=StrawberryDjangoSettings(
        FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
        TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
    ),
)
def test_field_metadata_overridden():
    """Test field metadata overriden.

    Test that the textual metadata from the Django model can be ignored in favor of
    custom metadata.
    """

    @strawberry_django.type(BookModel, description="A story with pages")
    class Book:
        title: auto = strawberry_django.field(description="The name of the story")

    type_def = get_object_definition(Book, strict=True)
    assert type_def.description == "A story with pages"
    title_field = type_def.get_field("title")
    assert title_field is not None
    assert title_field.description == "The name of the story"


@override_settings(
    STRAWBERRY_DJANGO=StrawberryDjangoSettings(
        FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
        TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
    ),
)
def test_field_no_empty_strings(monkeypatch: pytest.MonkeyPatch):
    """Test no empty strings on fields.

    Test that an empty Django model docstring doesn't get used for the description.
    """
    monkeypatch.setattr(BookModel, "__doc__", "")

    @strawberry_django.type(BookModel)
    class Book:
        title: auto

    assert get_object_definition(Book, strict=True).description is None


@strawberry_django.type(Color)
class ColorType:
    id: auto
    name: auto


@strawberry_django.type(Fruit)
class FruitType:
    id: auto
    name: auto

    @strawberry.field
    def color(self, info, root) -> "ColorType":
        return root.color


def test_type_resolution_with_resolvers():
    @strawberry.type
    class Query:
        fruit: FruitType = strawberry_django.field()

    schema = strawberry.Schema(query=Query)
    type_def = schema.get_type_by_name("FruitType")
    assert isinstance(type_def, StrawberryObjectDefinition)
    field = type_def.get_field("color")
    assert field
    assert field.type is ColorType
