import textwrap

import strawberry
from asgiref.sync import sync_to_async

import strawberry_django
from tests import models


def test_model_property(transactional_db):
    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto
        name_length: strawberry.auto

    @strawberry.type
    class Query:
        fruit: Fruit = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    assert (
        textwrap.dedent(str(schema))
        == textwrap.dedent(
            """\
    type Fruit {
      name: String!
      nameLength: Int!
    }

    type Query {
      fruit(pk: ID!): Fruit!
    }
    """,
        ).strip()
    )

    fruit1 = models.Fruit.objects.create(name="Banana")
    fruit2 = models.Fruit.objects.create(name="Apple")

    query = """
    query Fruit($pk: ID!) {
      fruit(pk: $pk) {
        name
        nameLength
      }
    }
    """

    for pk, name, length in [(fruit1.pk, "Banana", 6), (fruit2.pk, "Apple", 5)]:
        result = schema.execute_sync(query, variable_values={"pk": pk})
        assert result.errors is None
        assert result.data == {"fruit": {"name": name, "nameLength": length}}


async def test_model_property_async(transactional_db):
    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto
        name_length: strawberry.auto

    @strawberry.type
    class Query:
        fruit: Fruit = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    assert (
        textwrap.dedent(str(schema))
        == textwrap.dedent(
            """\
    type Fruit {
      name: String!
      nameLength: Int!
    }

    type Query {
      fruit(pk: ID!): Fruit!
    }
    """,
        ).strip()
    )

    fruit1 = await sync_to_async(models.Fruit.objects.create)(name="Banana")
    fruit2 = await sync_to_async(models.Fruit.objects.create)(name="Apple")

    query = """
    query Fruit($pk: ID!) {
      fruit(pk: $pk) {
        name
        nameLength
      }
    }
    """

    for pk, name, length in [(fruit1.pk, "Banana", 6), (fruit2.pk, "Apple", 5)]:
        result = await schema.execute(query, variable_values={"pk": pk})
        assert result.errors is None
        assert result.data == {"fruit": {"name": name, "nameLength": length}}
