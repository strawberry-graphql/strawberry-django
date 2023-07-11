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


@override_settings(
    STRAWBERRY_DJANGO=StrawberryDjangoSettings(
        FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
        TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
    ),
)
def test_all_fields_works():
    @strawberry_django.type(Fruit, fields="__all__")
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)
    assert type_def.description == "Fruit(id, name, color, sweetness)"

    name_field = type_def.get_field("name")
    assert name_field is not None
    assert name_field.type == str

    color_field = type_def.get_field("color")
    assert color_field is not None

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None
    assert sweetness_field.type == int
    assert sweetness_field.description == Fruit._meta.get_field("sweetness").help_text


def test_can_override_type_when_fields_all():
    @strawberry_django.type(Fruit, fields="__all__")
    class FruitType:
        name: int

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None
    assert name_field.type == int


def test_fields_can_be_enumerated():
    @strawberry_django.type(Fruit, fields=["name", "sweetness"])
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None

    color_field = type_def.get_field("color")
    assert color_field is None


def test_non_existent_fields_ignored():
    @strawberry_django.type(Fruit, fields=["name", "sourness"])
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None

    sourness_field = type_def.get_field("sourness")
    assert sourness_field is None


def test_resolvers_with_fields():
    @strawberry_django.type(Fruit, fields=["name"])
    class FruitType:
        @strawberry.field
        def color(self, info, root) -> "ColorType":
            return root.color

    @strawberry.type
    class Query:
        fruit: FruitType = strawberry_django.field()

    schema = strawberry.Schema(query=Query)
    type_def = schema.get_type_by_name("FruitType")

    color_field = type_def.get_field("color")
    assert color_field
    assert color_field.type is ColorType

    name_field = type_def.get_field("name")
    assert name_field is not None


def test_exclude_with_fields_is_ignored():
    @strawberry_django.type(Fruit, fields=["name", "sweetness"], exclude=["name"])
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None

    color_field = type_def.get_field("color")
    assert color_field is None


def test_exclude_includes_non_enumerated_fields():
    @strawberry_django.type(Fruit, exclude=["name"])
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is None

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None

    color_field = type_def.get_field("color")
    assert color_field is not None


def test_non_existent_fields_exclude_ignored():
    @strawberry_django.type(Fruit, exclude=["sourness"])
    class FruitType:
        pass

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None

    color_field = type_def.get_field("color")
    assert color_field is not None


def test_can_override_type_with_exclude():
    @strawberry_django.type(Fruit, exclude=["name"])
    class FruitType:
        sweetness: str

    type_def = get_object_definition(FruitType, strict=True)

    sweetness_field = type_def.get_field("sweetness")
    assert sweetness_field is not None
    assert sweetness_field.type == str


def test_can_override_fields_with_exclude():
    @strawberry_django.type(Fruit, exclude=["name"])
    class FruitType:
        name: auto

    type_def = get_object_definition(FruitType, strict=True)

    name_field = type_def.get_field("name")
    assert name_field is not None
