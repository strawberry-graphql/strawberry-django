from django.db import models
from strawberry_django import auto, fields
from typing import List
import pytest
import strawberry
import strawberry_django
from .. import utils

class TypeModel(models.Model):
    boolean = models.BooleanField()
    string = models.CharField(max_length=50)
    foreign_key = models.ForeignKey('TypeModel', blank=True,
            related_name='related_foreign_key', on_delete=models.CASCADE)
    one_to_one = models.OneToOneField('TypeModel', blank=True,
            related_name='related_one_to_one', on_delete=models.CASCADE)
    many_to_many = models.ManyToManyField('TypeModel',
            related_name='related_many_to_many')


def test_type():
    @strawberry_django.type(TypeModel)
    class Type:
        id: auto
        boolean: auto
        string: auto

    assert [(f.name, f.type) for f in fields(Type)] == [
        ('id', strawberry.ID),
        ('boolean', bool),
        ('string', str),
    ]


def test_inherit(testtype):
    @testtype(TypeModel)
    class Base:
        id: auto
        boolean: auto

    @strawberry_django.type(TypeModel)
    class Type(Base):
        string: auto

    assert [(f.name, f.type) for f in fields(Type)] == [
        ('id', strawberry.ID),
        ('boolean', bool),
        ('string', str),
    ]


def test_default_value():
    @strawberry_django.type(TypeModel)
    class Type:
        string: auto = 'data'
        string2: str = strawberry.field(default='data2')
        string3: str = strawberry_django.field(default='data3')

    assert [(f.name, f.type) for f in fields(Type)] == [
        ('string', str),
        ('string2', str),
        ('string3', str),
    ]
    assert Type().string == 'data'
    assert Type().string2 == 'data2'
    assert Type().string3 == 'data3'


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

    @strawberry_django.type(TypeModel)
    class Type(Base):
        pass

    assert [(f.name, f.type or f.child.type, f.is_list) for f in fields(Type)] == [
        ('foreign_key', strawberry_django.DjangoModelType, False),
        ('related_foreign_key', strawberry_django.DjangoModelType, True),
        ('one_to_one', strawberry_django.DjangoModelType, False),
        ('related_one_to_one', strawberry_django.DjangoModelType, False),
        ('many_to_many', strawberry_django.DjangoModelType, True),
        ('related_many_to_many', strawberry_django.DjangoModelType, True),
        ('another_name', strawberry_django.DjangoModelType, False),
    ]
