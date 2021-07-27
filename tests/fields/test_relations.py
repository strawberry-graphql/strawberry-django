from django.db import models
from strawberry.type import StrawberryList, StrawberryOptional

from strawberry_django import auto
from typing import List
import strawberry_django
import strawberry
import pytest

class ParentModel(models.Model):
    name = models.CharField(max_length=50);

class ChildModel(models.Model):
    name = models.CharField(max_length=50);
    parents = models.ManyToManyField(ParentModel, related_name='children')

@strawberry_django.type(ParentModel)
class Parent:
    id: auto
    name: auto
    children: List['Child']

@strawberry_django.type(ChildModel)
class Child:
    id: auto
    name: auto
    parents: List[Parent]


def test_relation():
    assert [(f.name, f.type or f.child.type, f.is_list) for f in Parent._type_definition.fields] == [
        ('id', strawberry.ID, False),
        ('name', str, False),
        ('children', StrawberryOptional(StrawberryList(Child)), True),
    ]


def test_reversed_relation():
    assert [(f.name, f.type or f.child.type, f.is_list) for f in Child._type_definition.fields] == [
        ('id', strawberry.ID, False),
        ('name', str, False),
        ('parents', StrawberryList(Parent), True),
    ]
