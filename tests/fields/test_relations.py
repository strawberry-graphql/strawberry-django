from typing import List, cast

import strawberry
from django.db import models
from strawberry import auto
from strawberry.type import StrawberryList, get_object_definition_strict

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField


class ParentModel(models.Model):
    name = models.CharField(max_length=50)


class ChildModel(models.Model):
    name = models.CharField(max_length=50)
    parents = models.ManyToManyField(ParentModel, related_name="children")


@strawberry_django.type(ParentModel)
class Parent:
    id: auto
    name: auto
    children: List["Child"]


@strawberry_django.type(ChildModel)
class Child:
    id: auto
    name: auto
    parents: List[Parent]


def test_relation():
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_list)
        for f in get_object_definition_strict(Parent).fields
    ] == [
        ("id", strawberry.ID, False),
        ("name", str, False),
        ("children", StrawberryList(Child), True),  # type: ignore
    ]


def test_reversed_relation():
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_list)
        for f in get_object_definition_strict(Child).fields
    ] == [
        ("id", strawberry.ID, False),
        ("name", str, False),
        ("parents", StrawberryList(Parent), True),  # type: ignore
    ]
