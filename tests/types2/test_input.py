from strawberry_django import auto, fields
from typing import List
import pytest
import strawberry
import strawberry_django
from .. import utils

from .test_type import TypeModel

def test_input():
    @strawberry_django.input(TypeModel)
    class Input:
        id: auto
        boolean: auto
        string: auto

    assert [(f.name, f.type) for f in fields(Input)] == [
        ('id', strawberry.ID),
        ('boolean', bool),
        ('string', str),
    ]


def test_inherit(testtype):
    @testtype(TypeModel)
    class Base:
        id: auto
        boolean: auto

    @strawberry_django.input(TypeModel)
    class Input(Base):
        string: auto

    assert [(f.name, f.type) for f in fields(Input)] == [
        ('id', strawberry.ID),
        ('boolean', bool),
        ('string', str),
    ]

def test_relationship(testtype):
    @strawberry_django.input(TypeModel)
    class Input:
        foreign_key: auto
        related_foreign_key: auto
        one_to_one: auto
        related_one_to_one: auto
        many_to_many: auto
        related_many_to_many: auto

    assert [(f.name, f.type) for f in fields(Input)] == [
        ('foreign_key', strawberry_django.OneToManyInput),
        ('related_foreign_key', strawberry_django.ManyToOneInput),
        ('one_to_one', strawberry_django.OneToOneInput),
        ('related_one_to_one', strawberry_django.OneToOneInput),
        ('many_to_many', strawberry_django.ManyToManyInput),
        ('related_many_to_many', strawberry_django.ManyToManyInput),
    ]


def test_relationship_inherit(testtype):
    @testtype(TypeModel)
    class Base:
        foreign_key: auto
        related_foreign_key: auto
        one_to_one: auto
        related_one_to_one: auto
        many_to_many: auto
        related_many_to_many: auto
        another_name: auto = strawberry_django.field(field_name='foreign_key')

    @strawberry_django.input(TypeModel)
    class Input(Base):
        pass

    assert [(f.name, f.type) for f in fields(Input)] == [
        ('foreign_key', strawberry_django.OneToManyInput),
        ('related_foreign_key', strawberry_django.ManyToOneInput),
        ('one_to_one', strawberry_django.OneToOneInput),
        ('related_one_to_one', strawberry_django.OneToOneInput),
        ('many_to_many', strawberry_django.ManyToManyInput),
        ('related_many_to_many', strawberry_django.ManyToManyInput),
        ('another_name', strawberry_django.OneToManyInput),
    ]
