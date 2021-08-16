from django.contrib import auth
from strawberry.type import StrawberryList, StrawberryOptional

import strawberry_django
from strawberry_django import auto, fields, DjangoModelType


def test_user_type():
    @strawberry_django.type(auth.models.User)
    class Type:
        username: auto
        email: auto
        groups: auto

    assert [(f.name, f.type or f.child.type) for f in fields(Type)] == [
        ('username', str),
        ('email', str),
        ('groups', StrawberryList(DjangoModelType)),
    ]


def test_group_type():
    @strawberry_django.type(auth.models.Group)
    class Type:
        name: auto
        users: auto = strawberry_django.field(field_name='user_set')

    assert [(f.name, f.type or f.child.type) for f in fields(Type)] == [
        ('name', str),
        ('users', StrawberryOptional(StrawberryList(DjangoModelType))),
    ]
