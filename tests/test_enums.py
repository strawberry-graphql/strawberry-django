import textwrap
from typing import cast

import strawberry
from django.db import models
from django.test import override_settings
from django.utils.translation import gettext_lazy
from django_choices_field import IntegerChoicesField, TextChoicesField
from pytest_mock import MockerFixture

import strawberry_django
from strawberry_django.fields import types
from strawberry_django.fields.types import field_type_map
from strawberry_django.settings import strawberry_django_settings


class Choice(models.TextChoices):
    """Choice description."""

    A = "a", "A description"
    B = "b", "B description"
    C = "c", gettext_lazy("C description")
    D = "12d-d'éléphant_🐘", "D description"
    E = "_2d_d__l_phant__", "E description"


class IntegerChoice(models.IntegerChoices):
    """IntegerChoice description."""

    X = 1, "1 description"
    Y = 2, "2 description"
    Z = 3, gettext_lazy("3 description")


class ChoicesModel(models.Model):
    attr1 = TextChoicesField(choices_enum=Choice)
    attr2 = IntegerChoicesField(choices_enum=IntegerChoice)
    attr3 = models.CharField(
        max_length=255,
        choices=[
            ("c", "C description"),
            ("d", gettext_lazy("D description")),
        ],
    )
    attr4 = models.IntegerField(
        choices=[
            (4, "4 description"),
            (5, gettext_lazy("5 description")),
        ],
    )
    attr5 = models.CharField(
        max_length=255,
        choices=Choice.choices,
    )
    attr6 = models.IntegerField(
        choices=IntegerChoice.choices,
    )


class ChoicesWithExtraFieldsModel(models.Model):
    attr1 = TextChoicesField(choices_enum=Choice)
    attr2 = IntegerChoicesField(choices_enum=IntegerChoice)
    attr3 = models.CharField(
        max_length=255,
        choices=[
            ("c", "C description"),
            ("d", gettext_lazy("D description")),
        ],
    )
    attr4 = models.IntegerField(
        choices=[
            (4, "4 description"),
            (5, gettext_lazy("5 description")),
        ],
    )
    attr5 = models.CharField(
        max_length=255,
        choices=Choice.choices,
    )
    attr6 = models.IntegerField(
        choices=IntegerChoice.choices,
    )
    extra1 = models.CharField(max_length=255)
    extra2 = models.PositiveIntegerField()


def test_choices_field():
    @strawberry_django.type(ChoicesModel)
    class ChoicesType:
        attr1: strawberry.auto
        attr2: strawberry.auto
        attr3: strawberry.auto
        attr4: strawberry.auto
        attr5: strawberry.auto
        attr6: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(
                ChoicesType,
                ChoicesModel(
                    attr1=Choice.A,
                    attr2=IntegerChoice.X,
                    attr3="c",
                    attr4=4,
                    attr5=Choice.A,
                    attr6=IntegerChoice.X,
                ),
            )

    expected = """\
    enum Choice {
      A
      B
      C
      D
      E
    }

    type ChoicesType {
      attr1: Choice!
      attr2: IntegerChoice!
      attr3: String!
      attr4: Int!
      attr5: String!
      attr6: Int!
    }

    enum IntegerChoice {
      X
      Y
      Z
    }

    type Query {
      obj: ChoicesType!
    }
    """

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        "query { obj { attr1, attr2, attr3, attr4, attr5, attr6 }}",
    )
    assert result.errors is None
    assert result.data == {
        "obj": {
            "attr1": "A",
            "attr2": "X",
            "attr3": "c",
            "attr4": 4,
            "attr5": "a",
            "attr6": 1,
        },
    }


def test_no_choices_enum(mocker: MockerFixture):
    # We can't use patch with the module name directly as it tries to resolve
    # strawberry.fields as a function instead of the module for python versions
    # before 3.11
    mocker.patch.object(types, "TextChoicesField", None)
    mocker.patch.dict(field_type_map, {TextChoicesField: str})
    mocker.patch.object(types, "IntegerChoicesField", None)
    mocker.patch.dict(field_type_map, {IntegerChoicesField: str})

    @strawberry_django.type(ChoicesModel)
    class ChoicesType:
        attr1: strawberry.auto
        attr2: strawberry.auto
        attr3: strawberry.auto
        attr4: strawberry.auto
        attr5: strawberry.auto
        attr6: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(
                ChoicesType,
                ChoicesModel(
                    attr1=Choice.A,
                    attr2=IntegerChoice.X,
                    attr3="c",
                    attr4=4,
                    attr5=Choice.A,
                    attr6=IntegerChoice.X,
                ),
            )

    expected = """\
    type ChoicesType {
      attr1: String!
      attr2: String!
      attr3: String!
      attr4: Int!
      attr5: String!
      attr6: Int!
    }

    type Query {
      obj: ChoicesType!
    }
    """

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        "query { obj { attr1, attr2, attr3, attr4, attr5, attr6 }}",
    )
    assert result.errors is None
    assert result.data == {
        "obj": {
            "attr1": "a",
            "attr2": "1",
            "attr3": "c",
            "attr4": 4,
            "attr5": "a",
            "attr6": 1,
        },
    }


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
        attr3: strawberry.auto
        attr4: strawberry.auto
        attr5: strawberry.auto
        attr6: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesType:
            return cast(
                ChoicesType,
                ChoicesModel(
                    attr1=Choice.A,
                    attr2=IntegerChoice.X,
                    attr3="c",
                    attr4=4,
                    attr5=Choice.A,
                    attr6=IntegerChoice.X,
                ),
            )

    expected = '''\
    enum Choice {
      A
      B
      C
      D
      E
    }

    type ChoicesType {
      attr1: Choice!
      attr2: IntegerChoice!
      attr3: TestsChoicesModelAttr3Enum!
      attr4: Int!
      attr5: TestsChoicesModelAttr5Enum!
      attr6: Int!
    }

    enum IntegerChoice {
      X
      Y
      Z
    }

    type Query {
      obj: ChoicesType!
    }

    enum TestsChoicesModelAttr3Enum {
      """C description"""
      c

      """D description"""
      d
    }

    enum TestsChoicesModelAttr5Enum {
      """A description"""
      a

      """B description"""
      b

      """C description"""
      c

      """D description"""
      _2d_d__l_phant__

      """E description"""
      _2d_d__l_phant___
    }
    '''

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        "query { obj { attr1, attr2, attr3, attr4, attr5, attr6 }}",
    )
    assert result.errors is None
    assert result.data == {
        "obj": {
            "attr1": "A",
            "attr2": "X",
            "attr3": "c",
            "attr4": 4,
            "attr5": "a",
            "attr6": 1,
        },
    }


@override_settings(
    STRAWBERRY_DJANGO={
        **strawberry_django_settings(),
        "GENERATE_ENUMS_FROM_CHOICES": True,
    },
)
def test_generate_choices_from_enum_with_extra_fields():
    @strawberry_django.type(ChoicesWithExtraFieldsModel)
    class ChoicesWithExtraFieldsType:
        attr1: strawberry.auto
        attr2: strawberry.auto
        attr3: strawberry.auto
        attr4: strawberry.auto
        attr5: strawberry.auto
        attr6: strawberry.auto
        extra1: strawberry.auto
        extra2: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.field
        def obj(self) -> ChoicesWithExtraFieldsType:
            return cast(
                ChoicesWithExtraFieldsType,
                ChoicesWithExtraFieldsModel(
                    attr1=Choice.A,
                    attr2=IntegerChoice.X,
                    attr3="c",
                    attr4=4,
                    attr5=Choice.A,
                    attr6=IntegerChoice.X,
                    extra1="str1",
                    extra2=99,
                ),
            )

    expected = '''\
    enum Choice {
      A
      B
      C
      D
      E
    }

    type ChoicesWithExtraFieldsType {
      attr1: Choice!
      attr2: IntegerChoice!
      attr3: TestsChoicesWithExtraFieldsModelAttr3Enum!
      attr4: Int!
      attr5: TestsChoicesWithExtraFieldsModelAttr5Enum!
      attr6: Int!
      extra1: String!
      extra2: Int!
    }

    enum IntegerChoice {
      X
      Y
      Z
    }

    type Query {
      obj: ChoicesWithExtraFieldsType!
    }

    enum TestsChoicesWithExtraFieldsModelAttr3Enum {
      """C description"""
      c

      """D description"""
      d
    }

    enum TestsChoicesWithExtraFieldsModelAttr5Enum {
      """A description"""
      a

      """B description"""
      b

      """C description"""
      c

      """D description"""
      _2d_d__l_phant__

      """E description"""
      _2d_d__l_phant___
    }


    '''

    schema = strawberry.Schema(query=Query)
    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()

    result = schema.execute_sync(
        "query { obj { attr1, attr2, attr3, attr4, attr5, attr6, extra1, extra2 }}",
    )
    assert result.errors is None
    assert result.data == {
        "obj": {
            "attr1": "A",
            "attr2": "X",
            "attr3": "c",
            "attr4": 4,
            "attr5": "a",
            "attr6": 1,
            "extra1": "str1",
            "extra2": 99,
        },
    }
