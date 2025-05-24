import textwrap
from typing import TYPE_CHECKING, cast

import strawberry
from django.db import models
from django.test import override_settings
from strawberry import BasePermission, auto, relay
from strawberry.types import get_object_definition

import strawberry_django
from strawberry_django.settings import strawberry_django_settings

if TYPE_CHECKING:
    from strawberry_django.fields.field import StrawberryDjangoField


class FieldAttributeModel(models.Model):
    field = models.CharField(max_length=50)


def test_default_django_name():
    @strawberry_django.type(FieldAttributeModel)
    class Type:
        field: auto
        field2: auto = strawberry_django.field(field_name="field")

    assert [
        (f.name, cast("StrawberryDjangoField", f).django_name)
        for f in get_object_definition(Type, strict=True).fields
    ] == [
        ("field", "field"),
        ("field2", "field"),
    ]


def test_field_permission_classes():
    class TestPermission(BasePermission):
        def has_permission(self, source, info, **kwargs):
            return True

    @strawberry_django.type(FieldAttributeModel)
    class Type:
        field: auto = strawberry.field(permission_classes=[TestPermission])

        @strawberry.field(permission_classes=[TestPermission])
        def custom_resolved_field(self) -> str:
            return self.field

    assert sorted(
        [
            (f.name, f.permission_classes)
            for f in get_object_definition(Type, strict=True).fields
        ],
    ) == sorted(
        [
            ("field", [TestPermission]),
            ("custom_resolved_field", [TestPermission]),
        ],
    )


def test_auto_id():
    @strawberry_django.filter_type(FieldAttributeModel)
    class MyTypeFilter:
        id: auto
        field: auto

    @strawberry_django.type(FieldAttributeModel)
    class MyType:
        id: auto
        other_id: auto = strawberry_django.field(field_name="id")
        field: auto

    @strawberry.type
    class Query:
        my_type: list[MyType] = strawberry_django.field(filters=MyTypeFilter)

    schema = strawberry.Schema(query=Query)
    expected = """\
    type MyType {
      id: ID!
      otherId: ID!
      field: String!
    }

    input MyTypeFilter {
      id: ID
      field: String
      AND: MyTypeFilter
      OR: MyTypeFilter
      NOT: MyTypeFilter
      DISTINCT: Boolean
    }

    type Query {
      myType(filters: MyTypeFilter): [MyType!]!
    }
    """
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


def test_auto_id_with_node():
    @strawberry_django.filter_type(FieldAttributeModel)
    class MyTypeFilter:
        id: auto
        field: auto

    @strawberry_django.type(FieldAttributeModel)
    class MyType(relay.Node):
        other_id: auto = strawberry_django.field(field_name="id")
        field: auto

    @strawberry.type
    class Query:
        my_type: list[MyType] = strawberry_django.field(filters=MyTypeFilter)

    schema = strawberry.Schema(query=Query)
    expected = '''\
    type MyType implements Node {
      """The Globally Unique ID of this object"""
      id: ID!
      otherId: ID!
      field: String!
    }

    input MyTypeFilter {
      id: ID
      field: String
      AND: MyTypeFilter
      OR: MyTypeFilter
      NOT: MyTypeFilter
      DISTINCT: Boolean
    }

    """An object with a Globally Unique ID"""
    interface Node {
      """The Globally Unique ID of this object"""
      id: ID!
    }

    type Query {
      myType(filters: MyTypeFilter): [MyType!]!
    }
    '''
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


@override_settings(
    STRAWBERRY_DJANGO={
        **strawberry_django_settings(),
        "MAP_AUTO_ID_AS_GLOBAL_ID": True,
    },
)
def test_auto_id_with_node_mapping_global_id():
    @strawberry_django.filter_type(FieldAttributeModel)
    class MyTypeFilter:
        id: auto
        field: auto

    @strawberry_django.type(FieldAttributeModel)
    class MyType(relay.Node):
        other_id: auto = strawberry_django.field(field_name="id")
        field: auto

    @strawberry.type
    class Query:
        my_type: list[MyType] = strawberry_django.field(filters=MyTypeFilter)

    schema = strawberry.Schema(query=Query)
    expected = '''\
    type MyType implements Node {
      """The Globally Unique ID of this object"""
      id: ID!
      otherId: ID!
      field: String!
    }

    input MyTypeFilter {
      id: ID
      field: String
      AND: MyTypeFilter
      OR: MyTypeFilter
      NOT: MyTypeFilter
      DISTINCT: Boolean
    }

    """An object with a Globally Unique ID"""
    interface Node {
      """The Globally Unique ID of this object"""
      id: ID!
    }

    type Query {
      myType(filters: MyTypeFilter): [MyType!]!
    }
    '''
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()
