from django.db import models
from strawberry_django import resolvers
import strawberry_django
import strawberry
import pytest

class ParentModel(models.Model):
    name = models.CharField(max_length=50);

class ChildModel(models.Model):
    name = models.CharField(max_length=50);
    parents = models.ManyToManyField(ParentModel, related_name='children')

@pytest.fixture
def types():
    return strawberry_django.TypeRegister()

@pytest.fixture
def parent(types):
    @types.register
    @strawberry_django.type(ParentModel, types=types)
    class Parent:
        pass
    return Parent

@pytest.fixture
def child(types):
    @types.register
    @strawberry_django.type(ChildModel, types=types)
    class Child:
        pass
    return Child


def test_basic(parent, child):
    assert [(f.name, f.type or f.child.type, f.is_list) for f in parent._type_definition.fields] == [
        ('children', child, True),
        ('id', strawberry.ID, False),
        ('name', str, False),
    ]

    assert [(f.name, f.type or f.child.type, f.is_list) for f in child._type_definition.fields] == [
        ('id', strawberry.ID, False),
        ('name', str, False),
        ('parents', parent, True),
    ]


def test_resolvers(parent, child):
    children = parent._type_definition.fields[0]
    assert children.name == 'children'
    assert children.base_resolver

    parents = child._type_definition.fields[2]
    assert parents.name == 'parents'
    assert parents.base_resolver


def test_unknown_type():
    with pytest.raises(TypeError, match="No type defined for Django model 'ChildModel'"):
        @strawberry_django.type(ParentModel, fields=['children'])
        class Parent:
            pass
