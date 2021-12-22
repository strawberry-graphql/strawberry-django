import strawberry_django
from strawberry_django import auto

from .models import User


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
