from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from typing_extensions import Annotated

import strawberry_django
from strawberry_django.fields.types import is_auto

from .models import User


def test_is_auto():
    assert is_auto(auto) is True
    assert is_auto(object) is False


def test_is_auto_with_annotation():
    annotation = StrawberryAnnotation(auto)
    assert is_auto(annotation) is True
    str_annotation = StrawberryAnnotation("auto", namespace=globals())
    assert is_auto(str_annotation) is True


def test_is_auto_with_annotated():
    assert is_auto(Annotated[auto, object()]) is True
    assert is_auto(Annotated[str, auto]) is False


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
