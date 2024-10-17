from typing import Optional, cast

import strawberry
from django.db import models
from strawberry import auto
from strawberry.types import get_object_definition
from strawberry.types.base import (
    StrawberryList,
    StrawberryOptional,
)

import strawberry_django
from strawberry_django.fields.field import StrawberryDjangoField


class ParentModel(models.Model):
    name = models.CharField(max_length=50)


class OneToOneModel(models.Model):
    name = models.CharField(max_length=50)
    parent = models.OneToOneField(
        ParentModel,
        on_delete=models.SET_NULL,
        related_name="one_to_one",
        null=True,
        blank=True,
    )


class ChildModel(models.Model):
    name = models.CharField(max_length=50)
    parents = models.ManyToManyField(ParentModel, related_name="children")


@strawberry_django.type(ParentModel)
class Parent:
    id: auto
    name: auto
    children: list["Child"]
    one_to_one: Optional["OneToOne"]


@strawberry_django.type(OneToOneModel)
class OneToOne:
    id: auto
    name: auto
    parent: Optional["Parent"]


@strawberry_django.type(ChildModel)
class Child:
    id: auto
    name: auto
    parents: list[Parent]


def test_relation():
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_list)
        for f in get_object_definition(Parent, strict=True).fields
    ] == [
        ("id", strawberry.ID, False),
        ("name", str, False),
        ("children", StrawberryList(Child), True),
        ("one_to_one", StrawberryOptional(OneToOne), False),
    ]


def test_reversed_relation():
    assert [
        (f.name, f.type, cast(StrawberryDjangoField, f).is_list)
        for f in get_object_definition(Child, strict=True).fields
    ] == [
        ("id", strawberry.ID, False),
        ("name", str, False),
        ("parents", StrawberryList(Parent), True),
    ]


def test_relation_query(transactional_db):
    @strawberry.type
    class Query:
        parent: Parent = strawberry_django.field()
        one_to_one: OneToOne = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    query = """\
    query Query ($pk: ID!) {
      parent (pk: $pk) {
        name
        oneToOne {
          name
        }
        children {
          id
          name
        }
      }
    }
    """

    parent = ParentModel.objects.create(name="Parent")
    result = schema.execute_sync(query, {"pk": parent.pk})
    assert result.errors is None
    assert result.data == {
        "parent": {"children": [], "name": "Parent", "oneToOne": None},
    }

    OneToOneModel.objects.create(name="OneToOne", parent=parent)
    result = schema.execute_sync(query, {"pk": parent.pk})
    assert result.errors is None
    assert result.data == {
        "parent": {"children": [], "name": "Parent", "oneToOne": {"name": "OneToOne"}},
    }

    child1 = ChildModel.objects.create(name="Child1")
    child2 = ChildModel.objects.create(name="Child2")
    ChildModel.objects.create(name="Child3")

    child1.parents.add(parent)
    child2.parents.add(parent)
    result = schema.execute_sync(query, {"pk": parent.pk})
    assert result.errors is None
    assert result.data == {
        "parent": {
            "children": [{"id": "1", "name": "Child1"}, {"id": "2", "name": "Child2"}],
            "name": "Parent",
            "oneToOne": {"name": "OneToOne"},
        },
    }
