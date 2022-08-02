from pytest import MonkeyPatch
from strawberry import auto

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField

from .models import Book as BookModel, User


def test_type_instance():
    @strawberry_django.type(User)
    class UserType:
        id: auto
        name: auto

    user = UserType(1, "user")
    assert user.id == 1
    assert user.name == "user"


def test_type_instance_auto_as_str():
    @strawberry_django.type(User)
    class UserType:
        id: "auto"
        name: "auto"

    user = UserType(1, "user")
    assert user.id == 1
    assert user.name == "user"


def test_input_instance():
    @strawberry_django.input(User)
    class InputType:
        id: auto
        name: auto

    user = InputType(1, "user")
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
        for field in UserType._type_definition.fields
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
        UserType._type_definition.get_field("id"), CustomStrawberryDjangoField
    )
    assert isinstance(
        UserType._type_definition.get_field("name"), StrawberryDjangoField
    )
    assert not isinstance(
        UserType._type_definition.get_field("name"), CustomStrawberryDjangoField
    )


def test_field_metadata_preserved():
    """
    Test that textual metadata from the Django model is reflected in the Strawberry type.
    """

    @strawberry_django.type(BookModel)
    class Book:
        title: auto

    assert Book._type_definition.description == BookModel.__doc__
    assert (
        Book._type_definition.get_field("title").description
        == BookModel._meta.get_field("title").help_text
    )


def test_field_metadata_overridden():
    """
    Test that the textual metadata from the Django model can be ignored in favor of
    custom metadata.
    """

    @strawberry_django.type(BookModel, description="A story with pages")
    class Book:
        title: auto = strawberry_django.field(description="The name of the story")

    assert Book._type_definition.description == "A story with pages"
    assert (
        Book._type_definition.get_field("title").description == "The name of the story"
    )


def test_field_no_empty_strings(monkeypatch: MonkeyPatch):
    """
    Test that an empty Django model docstring doesn't get used for the description.
    """
    monkeypatch.setattr(BookModel, "__doc__", "")

    @strawberry_django.type(BookModel)
    class Book:
        title: auto

    assert Book._type_definition.description is None
