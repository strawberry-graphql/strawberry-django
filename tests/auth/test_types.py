import strawberry
from django.contrib.auth.models import Group, User
from strawberry.type import StrawberryList, get_object_definition

import strawberry_django
from strawberry_django import DjangoModelType


def test_user_type():
    @strawberry_django.type(User)
    class Type:
        username: strawberry.auto
        email: strawberry.auto
        groups: strawberry.auto

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("username", str),
        ("email", str),
        ("groups", StrawberryList(DjangoModelType)),
    ]


def test_group_type():
    @strawberry_django.type(Group)
    class Type:
        name: strawberry.auto
        users: strawberry.auto = strawberry_django.field(field_name="user_set")

    object_definition = get_object_definition(Type, strict=True)
    assert [(f.name, f.type) for f in object_definition.fields] == [
        ("name", str),
        ("users", StrawberryList(DjangoModelType)),
    ]
