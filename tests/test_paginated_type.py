import textwrap

import pytest
import strawberry

import strawberry_django
from strawberry_django.pagination import OffsetPaginated
from tests import models


def test_paginated_schema():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.type(models.Color)
    class Color:
        id: int
        name: str
        fruits: OffsetPaginated[Fruit]

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.field()
        colors: OffsetPaginated[Color] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    expected = '''\
    type Color {
      id: Int!
      name: String!
      fruits(pagination: OffsetPaginationInput): FruitOffsetPaginated!
    }

    type ColorOffsetPaginated {
      pageInfo: OffsetPaginationInfo!

      """Total count of existing results."""
      totalCount: Int!

      """List of paginated results."""
      results: [Color!]!
    }

    type Fruit {
      id: Int!
      name: String!
    }

    type FruitOffsetPaginated {
      pageInfo: OffsetPaginationInfo!

      """Total count of existing results."""
      totalCount: Int!

      """List of paginated results."""
      results: [Fruit!]!
    }

    type OffsetPaginationInfo {
      offset: Int!
      limit: Int
    }

    input OffsetPaginationInput {
      offset: Int! = 0
      limit: Int = null
    }

    type Query {
      fruits(pagination: OffsetPaginationInput): FruitOffsetPaginated!
      colors(pagination: OffsetPaginationInput): ColorOffsetPaginated!
    }
    '''

    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


@pytest.mark.django_db(transaction=True)
def test_pagination_query():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.field()

    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Banana")
    models.Fruit.objects.create(name="Strawberry")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits ($pagination: OffsetPaginationInput) {
      fruits (pagination: $pagination) {
        totalCount
        results {
          name
        }
      }
    }
    """

    res = schema.execute_sync(query)
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Apple"}, {"name": "Banana"}, {"name": "Strawberry"}],
        }
    }

    res = schema.execute_sync(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Apple"}],
        }
    }

    res = schema.execute_sync(
        query, variable_values={"pagination": {"limit": 1, "offset": 1}}
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Banana"}],
        }
    }


@pytest.mark.django_db(transaction=True)
async def test_pagination_query_async():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.field()

    await models.Fruit.objects.acreate(name="Apple")
    await models.Fruit.objects.acreate(name="Banana")
    await models.Fruit.objects.acreate(name="Strawberry")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits ($pagination: OffsetPaginationInput) {
      fruits (pagination: $pagination) {
        totalCount
        results {
          name
        }
      }
    }
    """

    res = await schema.execute(query)
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Apple"}, {"name": "Banana"}, {"name": "Strawberry"}],
        }
    }

    res = await schema.execute(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Apple"}],
        }
    }

    res = await schema.execute(
        query, variable_values={"pagination": {"limit": 1, "offset": 1}}
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [{"name": "Banana"}],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_pagination_nested_query():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.type(models.Color)
    class Color:
        id: int
        name: str
        fruits: OffsetPaginated[Fruit]

    @strawberry.type
    class Query:
        colors: OffsetPaginated[Color] = strawberry_django.field()

    red = models.Color.objects.create(name="Red")
    yellow = models.Color.objects.create(name="Yellow")

    models.Fruit.objects.create(name="Apple", color=red)
    models.Fruit.objects.create(name="Banana", color=yellow)
    models.Fruit.objects.create(name="Strawberry", color=red)

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetColors ($pagination: OffsetPaginationInput) {
      colors {
        totalCount
        results {
          fruits (pagination: $pagination) {
            totalCount
            results {
              name
            }
          }
        }
      }
    }
    """

    res = schema.execute_sync(query)
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Apple"}, {"name": "Strawberry"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [{"name": "Banana"}],
                    }
                },
            ],
        }
    }

    res = schema.execute_sync(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Apple"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [{"name": "Banana"}],
                    }
                },
            ],
        }
    }

    res = schema.execute_sync(
        query, variable_values={"pagination": {"limit": 1, "offset": 1}}
    )
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Strawberry"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [],
                    }
                },
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
async def test_pagination_nested_query_async():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.type(models.Color)
    class Color:
        id: int
        name: str
        fruits: OffsetPaginated[Fruit]

    @strawberry.type
    class Query:
        colors: OffsetPaginated[Color] = strawberry_django.field()

    red = await models.Color.objects.acreate(name="Red")
    yellow = await models.Color.objects.acreate(name="Yellow")

    await models.Fruit.objects.acreate(name="Apple", color=red)
    await models.Fruit.objects.acreate(name="Banana", color=yellow)
    await models.Fruit.objects.acreate(name="Strawberry", color=red)

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetColors ($pagination: OffsetPaginationInput) {
      colors {
        totalCount
        results {
          fruits (pagination: $pagination) {
            totalCount
            results {
              name
            }
          }
        }
      }
    }
    """

    res = await schema.execute(query)
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Apple"}, {"name": "Strawberry"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [{"name": "Banana"}],
                    }
                },
            ],
        }
    }

    res = await schema.execute(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Apple"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [{"name": "Banana"}],
                    }
                },
            ],
        }
    }

    res = await schema.execute(
        query, variable_values={"pagination": {"limit": 1, "offset": 1}}
    )
    assert res.errors is None
    assert res.data == {
        "colors": {
            "totalCount": 2,
            "results": [
                {
                    "fruits": {
                        "totalCount": 2,
                        "results": [{"name": "Strawberry"}],
                    }
                },
                {
                    "fruits": {
                        "totalCount": 1,
                        "results": [],
                    }
                },
            ],
        }
    }
