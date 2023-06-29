import textwrap
from typing import cast

import strawberry
from django.db import models
from django.test import override_settings
from django_choices_field import TextChoicesField
from pytest_mock import MockerFixture

import strawberry_django
from strawberry_django.fields import types
from strawberry_django.fields.types import field_type_map
from strawberry_django.settings import (
    strawberry_django_settings,
)


class Choice(models.TextChoices):
    """Choice description."""

    A = "a", "A description"
    B = "b", "B description"
    C = "c", "C description"


class ChoicesModel(models.Model):
    attr1 = TextChoicesField(choices_enum=Choice)
    attr2 = models.CharField(
        max_length=255,
        choices=[
            ("c", "C description"),
            ("d", "D description"),
        ],
    )


def test_choices_field():
    @strawberry_django.type(ChoicesModel)
    class ChoicesType:
        attr1: strawberry.auto
        attr2: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(ChoicesType, ChoicesModel(attr1=Choice.A, attr2="c"))

    expected = """\
    enum Choice {
      A
      B
      C
    }

    type ChoicesType {
      attr1: Choice!
      attr2: String!
    }

    type Query {
      obj: ChoicesType!
    }
    """

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync("query { obj { attr1, attr2 }}")
    assert result.errors is None
    assert result.data == {"obj": {"attr1": "A", "attr2": "c"}}


def test_no_choices_enum(mocker: MockerFixture):
    # We can't use patch with the module name directly as it tries to resolve
    # strawberry.fields as a function instead of the module for python versions
    # before 3.11
    mocker.patch.object(types, "TextChoicesField", None)
    mocker.patch.dict(field_type_map, {TextChoicesField: str})

    @strawberry_django.type(ChoicesModel)
    class ChoicesType:
        attr1: strawberry.auto
        attr2: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(ChoicesType, ChoicesModel(attr1=Choice.A, attr2="c"))

    expected = """\
    type ChoicesType {
      attr1: String!
      attr2: String!
    }

    type Query {
      obj: ChoicesType!
    }
    """

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync("query { obj { attr1, attr2 }}")
    assert result.errors is None
    assert result.data == {"obj": {"attr1": "a", "attr2": "c"}}


@override_settings(
    STRAWBERRY_DJANGO={
        **strawberry_django_settings(),
        "GENERATE_ENUMS_FROM_CHOICES": True,
    },
)
def test_generate_choices_from_enum():
    @strawberry_django.type(ChoicesModel)
    class ChoicesType:
        attr1: strawberry.auto
        attr2: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(ChoicesType, ChoicesModel(attr1=Choice.A, attr2="c"))

    expected = '''\
    enum Choice {
      A
      B
      C
    }

    type ChoicesType {
      attr1: Choice!
      attr2: TestsChoicesModelAttr2Enum!
    }

    type Query {
      obj: ChoicesType!
    }

    enum TestsChoicesModelAttr2Enum {
      """C description"""
      c

      """D description"""
      d
    }
    '''

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync("query { obj { attr1, attr2 }}")
    assert result.errors is None
    assert result.data == {"obj": {"attr1": "A", "attr2": "c"}}
