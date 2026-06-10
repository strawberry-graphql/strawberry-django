import textwrap
from typing import Annotated

import pytest
import strawberry
from django.db import connection
from django.db.models import Q, QuerySet
from django.test.utils import CaptureQueriesContext, override_settings
from strawberry.extensions.field_extension import FieldExtension

import strawberry_django
from strawberry_django.fields import field as field_mod
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated, OffsetPaginationInput
from strawberry_django.settings import StrawberryDjangoSettings
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
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()
        colors: OffsetPaginated[Color] = strawberry_django.offset_paginated()

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
      limit: Int
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
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

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
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

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


@strawberry_django.type(models.Fruit)
class FruitLazyTest:
    id: int
    name: str


@strawberry_django.type(models.Color)
class ColorLazyTest:
    id: int
    name: str
    fruits: OffsetPaginated[
        Annotated["FruitLazyTest", strawberry.lazy("tests.test_paginated_type")]
    ] = strawberry_django.offset_paginated()


@pytest.mark.django_db(transaction=True)
def test_pagination_with_lazy_type_and_django_query_optimizer():
    @strawberry.type
    class Query:
        colors: OffsetPaginated[ColorLazyTest] = strawberry_django.offset_paginated()

    red = models.Color.objects.create(name="Red")
    yellow = models.Color.objects.create(name="Yellow")

    models.Fruit.objects.create(name="Apple", color=red)
    models.Fruit.objects.create(name="Banana", color=yellow)
    models.Fruit.objects.create(name="Strawberry", color=red)

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

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
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

    @strawberry.type
    class Query:
        colors: OffsetPaginated[Color] = strawberry_django.offset_paginated()

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
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

    @strawberry.type
    class Query:
        colors: OffsetPaginated[Color] = strawberry_django.offset_paginated()

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


@pytest.mark.django_db(transaction=True)
def test_pagination_query_with_subclass():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class FruitPaginated(OffsetPaginated[Fruit]):
        _custom_field: strawberry.Private[str]

        @strawberry_django.field
        def custom_field(self) -> str:
            return self._custom_field

        @classmethod
        def resolve_paginated(cls, queryset, *, info, pagination=None, **kwargs):
            return cls(
                queryset=queryset,
                pagination=pagination or OffsetPaginationInput(),
                _custom_field="pagination rocks",
            )

    @strawberry.type
    class Query:
        fruits: FruitPaginated = strawberry_django.offset_paginated()

    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Banana")
    models.Fruit.objects.create(name="Strawberry")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits ($pagination: OffsetPaginationInput) {
      fruits (pagination: $pagination) {
        totalCount
        customField
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
            "customField": "pagination rocks",
            "results": [{"name": "Apple"}, {"name": "Banana"}, {"name": "Strawberry"}],
        }
    }

    res = schema.execute_sync(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "customField": "pagination rocks",
            "results": [{"name": "Apple"}],
        }
    }

    res = schema.execute_sync(
        query, variable_values={"pagination": {"limit": 1, "offset": 2}}
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "customField": "pagination rocks",
            "results": [{"name": "Strawberry"}],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_pagination_query_with_resolver_schema():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.filter_type(models.Fruit)
    class FruitFilter:
        name: str

    @strawberry_django.order(models.Fruit)
    class FruitOrder:
        name: str

    @strawberry.type
    class Query:
        @strawberry_django.offset_paginated(OffsetPaginated[Fruit])
        def fruits(self) -> QuerySet[models.Fruit]: ...

        @strawberry_django.offset_paginated(
            OffsetPaginated[Fruit],
            filters=FruitFilter,
            order=FruitOrder,
        )
        def fruits_with_order_and_filter(self) -> QuerySet[models.Fruit]: ...

    schema = strawberry.Schema(query=Query)

    expected = '''
    type Fruit {
      id: Int!
      name: String!
    }

    input FruitFilter {
      name: String!
      AND: FruitFilter
      OR: FruitFilter
      NOT: FruitFilter
      DISTINCT: Boolean
    }

    type FruitOffsetPaginated {
      pageInfo: OffsetPaginationInfo!

      """Total count of existing results."""
      totalCount: Int!

      """List of paginated results."""
      results: [Fruit!]!
    }

    input FruitOrder {
      name: String
    }

    type OffsetPaginationInfo {
      offset: Int!
      limit: Int
    }

    input OffsetPaginationInput {
      offset: Int! = 0
      limit: Int
    }

    type Query {
      fruits(pagination: OffsetPaginationInput): FruitOffsetPaginated!
      fruitsWithOrderAndFilter(filters: FruitFilter, order: FruitOrder, pagination: OffsetPaginationInput): FruitOffsetPaginated!
    }
    '''

    assert textwrap.dedent(str(schema)) == textwrap.dedent(expected).strip()


@pytest.mark.django_db(transaction=True)
def test_pagination_query_with_resolver():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.filter_type(models.Fruit)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.order(models.Fruit)
    class FruitOrder:
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.offset_paginated(OffsetPaginated[Fruit])
        def fruits(self) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.filter(name__startswith="S")

        @strawberry_django.offset_paginated(
            OffsetPaginated[Fruit],
            filters=FruitFilter,
            order=FruitOrder,
        )
        def fruits_with_order_and_filter(self) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.filter(name__startswith="S")

    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Strawberry")
    models.Fruit.objects.create(name="Banana")
    models.Fruit.objects.create(name="Sugar Apple")
    models.Fruit.objects.create(name="Starfruit")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits (
      $pagination: OffsetPaginationInput
      $filters: FruitFilter
      $order: FruitOrder
    ) {
      fruits (pagination: $pagination) {
        totalCount
        results {
          name
        }
      }
      fruitsWithOrderAndFilter (
        pagination: $pagination
        filters: $filters
        order: $order
      ) {
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
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
                {"name": "Starfruit"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
                {"name": "Starfruit"},
            ],
        },
    }

    res = schema.execute_sync(query, variable_values={"pagination": {"limit": 1}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
            ],
        },
    }

    res = schema.execute_sync(
        query,
        variable_values={
            "pagination": {"limit": 2},
            "order": {"name": "ASC"},
            "filters": {"name": "Strawberry"},
        },
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 1,
            "results": [
                {"name": "Strawberry"},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_pagination_query_with_resolver_arguments():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry_django.filter_type(models.Fruit)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.order(models.Fruit)
    class FruitOrder:
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry_django.offset_paginated(OffsetPaginated[Fruit])
        def fruits(self, starts_with: str) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.filter(name__startswith=starts_with)

        @strawberry_django.offset_paginated(
            OffsetPaginated[Fruit],
            filters=FruitFilter,
            order=FruitOrder,
        )
        def fruits_with_order_and_filter(
            self, starts_with: str
        ) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.filter(name__startswith=starts_with)

    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Strawberry")
    models.Fruit.objects.create(name="Banana")
    models.Fruit.objects.create(name="Sugar Apple")
    models.Fruit.objects.create(name="Starfruit")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits (
      $pagination: OffsetPaginationInput
      $filters: FruitFilter
      $order: FruitOrder
      $startsWith: String!
    ) {
      fruits (startsWith: $startsWith, pagination: $pagination) {
        totalCount
        results {
          name
        }
      }
      fruitsWithOrderAndFilter (
        startsWith: $startsWith
        pagination: $pagination
        filters: $filters
        order: $order
      ) {
        totalCount
        results {
          name
        }
      }
    }
    """

    res = schema.execute_sync(query, variable_values={"startsWith": "S"})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
                {"name": "Starfruit"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
                {"name": "Starfruit"},
            ],
        },
    }

    res = schema.execute_sync(
        query,
        variable_values={"startsWith": "S", "pagination": {"limit": 1}},
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
            ],
        },
    }

    res = schema.execute_sync(
        query,
        variable_values={
            "startsWith": "S",
            "pagination": {"limit": 2},
            "order": {"name": "ASC"},
            "filters": {"name": "Strawberry"},
        },
    )
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 3,
            "results": [
                {"name": "Strawberry"},
                {"name": "Sugar Apple"},
            ],
        },
        "fruitsWithOrderAndFilter": {
            "totalCount": 1,
            "results": [
                {"name": "Strawberry"},
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
@override_settings(
    STRAWBERRY_DJANGO=StrawberryDjangoSettings(  # type: ignore
        PAGINATION_DEFAULT_LIMIT=2,
    ),
)
def test_pagination_default_limit():
    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Banana")
    models.Fruit.objects.create(name="Strawberry")
    models.Fruit.objects.create(name="Watermelon")

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
            "totalCount": 4,
            "results": [{"name": "Apple"}, {"name": "Banana"}],
        }
    }

    res = schema.execute_sync(query, variable_values={"pagination": {"offset": 1}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 4,
            "results": [{"name": "Banana"}, {"name": "Strawberry"}],
        }
    }

    # Setting limit to None should use default limit (same as not providing limit)
    res = schema.execute_sync(query, variable_values={"pagination": {"limit": None}})
    assert res.errors is None
    assert res.data == {
        "fruits": {
            "totalCount": 4,
            "results": [
                {"name": "Apple"},
                {"name": "Banana"},
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("requested_limit", "max_limit", "default_limit", "expected_limit"),
    [
        (5, None, 100, 5),  # Explicit limit should be honored
        (None, 50, 20, 20),  # None should use default_limit
        (None, 50, None, 50),  # None with no default should use max_limit
        (None, None, 20, 20),  # None with no max should use default_limit
        (100, 50, 20, 50),  # Limit > max should be capped to max_limit
        ("UNSET", 50, 20, 20),  # UNSET should use default_limit
        ("UNSET", None, 20, 20),  # UNSET with no max should use default_limit
        (10, 50, 5, 10),  # Explicit limit < max should be honored
        # Edge cases
        (
            None,
            None,
            None,
            100,
        ),  # None with no settings should use global default (100)
        ("UNSET", 50, None, 50),  # UNSET with no default should fall back to max_limit
        (
            "UNSET",
            None,
            None,
            100,
        ),  # UNSET with no settings should use global default (100)
        (-5, 50, 20, 50),  # Negative limit should clamp to max_limit when set
        (
            -5,
            None,
            20,
            100,
        ),  # Negative limit without explicit max clamps to the default max (100)
        (
            -5,
            None,
            None,
            100,
        ),  # Negative limit without any settings clamps to the default max (100)
        # Large positive limits should be clamped to max_limit
        (
            9999999,
            None,
            None,
            100,
        ),  # Very large limit with default settings → clamped to default max (100)
        (
            9999999,
            500,
            20,
            500,
        ),  # Very large limit with overridden max → clamped to max_limit
    ],
)
def test_page_info_reflects_effective_limit(
    requested_limit, max_limit, default_limit, expected_limit
):
    """Test that pageInfo.limit reflects the actual limit applied, not the requested one."""

    @strawberry_django.type(models.Fruit)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()

    for i in range(10):
        models.Fruit.objects.create(name=f"Fruit{i}")

    schema = strawberry.Schema(query=Query)

    query = """\
    query GetFruits ($pagination: OffsetPaginationInput) {
      fruits (pagination: $pagination) {
        pageInfo {
          limit
          offset
        }
        totalCount
        results {
          name
        }
      }
    }
    """

    settings_dict = {}
    if max_limit is not None:
        settings_dict["PAGINATION_MAX_LIMIT"] = max_limit
    if default_limit is not None:
        settings_dict["PAGINATION_DEFAULT_LIMIT"] = default_limit

    with override_settings(STRAWBERRY_DJANGO=settings_dict):
        if requested_limit == "UNSET":
            # Don't provide pagination at all
            res = schema.execute_sync(query)
        elif requested_limit is None:
            # Explicitly pass null
            res = schema.execute_sync(
                query, variable_values={"pagination": {"limit": None}}
            )
        else:
            # Pass explicit limit
            res = schema.execute_sync(
                query, variable_values={"pagination": {"limit": requested_limit}}
            )

    assert res.errors is None
    assert res.data is not None
    assert res.data["fruits"]["pageInfo"]["limit"] == expected_limit
    assert res.data["fruits"]["pageInfo"]["offset"] == 0

    results = res.data["fruits"]["results"]
    total_fruits = 10
    if expected_limit is not None and expected_limit > 0:
        expected_count = min(expected_limit, total_fruits)
    else:
        expected_count = total_fruits
    assert len(results) == expected_count


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_extensions_receive_filters():
    @strawberry_django.filter_type(models.Fruit, lookups=True)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class Fruit:
        id: int
        name: str

    class CaptureKwargsExtension(FieldExtension):
        def __init__(self):
            super().__init__()
            self.seen_kwargs: dict[str, object] | None = None

        def resolve(self, next_, source, info, **kwargs):
            self.seen_kwargs = dict(kwargs)
            return next_(source, info, **kwargs)

    extension = CaptureKwargsExtension()

    @strawberry.type
    class Query:
        @strawberry_django.offset_paginated(
            OffsetPaginated[Fruit],
            filters=FruitFilter,
            extensions=[extension],
        )
        def fruits(self) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.all()

    schema = strawberry.Schema(query=Query)
    models.Fruit.objects.create(name="Apple")

    query = """
      query ($filters: FruitFilter) {
        fruits(filters: $filters) {
          results {
            name
          }
        }
      }
    """

    res = schema.execute_sync(
        query,
        variable_values={"filters": {"name": {"exact": "Apple"}}},
    )

    assert res.errors is None
    assert extension.seen_kwargs is not None
    assert "filters" in extension.seen_kwargs


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_allows_filters_without_resolver_param():
    @strawberry_django.filter_type(models.Fruit, lookups=True)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        @strawberry_django.offset_paginated(
            OffsetPaginated[Fruit],
            filters=FruitFilter,
        )
        def fruits(self) -> QuerySet[models.Fruit]:
            return models.Fruit.objects.all()

    schema = strawberry.Schema(query=Query)
    models.Fruit.objects.create(name="Apple")
    models.Fruit.objects.create(name="Banana")

    query = """
      query ($filters: FruitFilter) {
        fruits(filters: $filters) {
          results {
            name
          }
        }
      }
    """

    res = schema.execute_sync(
        query,
        variable_values={"filters": {"name": {"exact": "Apple"}}},
    )

    assert res.errors is None
    assert res.data == {"fruits": {"results": [{"name": "Apple"}]}}


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_applies_filter_pipeline_only_once():
    """The filter pipeline must run exactly once per OffsetPaginated resolution.

    The OffsetPaginated extension forwards ``filters``/``order``/``pagination`` to
    the inner resolver so extensions and custom resolvers can read them (see
    ``test_offset_paginated_extensions_receive_filters``, added for #853/#854).
    The inner resolver already applies them via ``get_queryset``; the extension
    must therefore NOT re-apply them in its own ``get_queryset`` closure.

    Re-applying runs the whole filter pipeline twice. For a filter that spans a
    multivalued relation, the second ``queryset.filter(...)`` makes Django emit a
    *second*, independent set of JOINs, squaring the row count of the query (this
    is what took a production query from <1s to >30s).
    """
    call_count = 0

    @strawberry_django.filter_type(models.Fruit)
    class FruitFilter:
        @strawberry_django.filter_field
        def name_contains(self, queryset, value: str, prefix: str):
            nonlocal call_count
            call_count += 1
            return queryset, Q(**{f"{prefix}name__icontains": value})

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated(
            filters=FruitFilter
        )

    schema = strawberry.Schema(query=Query)
    models.Fruit.objects.create(name="Apple")

    query = """
      query ($filters: FruitFilter) {
        fruits(filters: $filters) {
          results { name }
        }
      }
    """
    res = schema.execute_sync(
        query, variable_values={"filters": {"nameContains": "App"}}
    )

    assert res.errors is None
    assert res.data == {"fruits": {"results": [{"name": "Apple"}]}}
    assert call_count == 1, (
        f"filter pipeline ran {call_count} times for a single OffsetPaginated "
        "resolution (expected 1); it is being applied twice"
    )


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_does_not_duplicate_relation_joins():
    """Filtering an OffsetPaginated field on a relation must not double the JOINs.

    Regression test for the double-filter bug: an OffsetPaginated field must emit
    the same relation JOINs as the equivalent non-paginated list field. The bug
    applied the filter twice, so the paginated query joined the related table
    twice (e.g. ``tests_group_tags`` appearing as two aliases), squaring rows.
    """

    @strawberry_django.filter_type(models.Tag, lookups=True)
    class TagFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(models.Group, lookups=True)
    class GroupFilter:
        name: strawberry.auto
        tags: TagFilter | None

    @strawberry_django.type(models.Group, filters=GroupFilter)
    class GroupType:
        id: int
        name: str

    @strawberry.type
    class Query:
        groups_paginated: OffsetPaginated[GroupType] = (
            strawberry_django.offset_paginated(filters=GroupFilter)
        )
        groups_list: list[GroupType] = strawberry_django.field(filters=GroupFilter)

    schema = strawberry.Schema(query=Query)
    group = models.Group.objects.create(name="g1")
    tag = models.Tag.objects.create(name="t1")
    group.tags.add(tag)

    variables = {"filters": {"tags": {"name": {"exact": "t1"}}}}

    list_query = """
      query ($filters: GroupFilter) {
        groupsList(filters: $filters) { name }
      }
    """
    with CaptureQueriesContext(connection) as list_ctx:
        list_res = schema.execute_sync(list_query, variable_values=variables)
    assert list_res.errors is None
    list_sql = next(
        q["sql"]
        for q in list_ctx.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT") and "tests_group" in q["sql"]
    )
    list_joins = list_sql.upper().count(" JOIN ")

    paginated_query = """
      query ($filters: GroupFilter) {
        groupsPaginated(filters: $filters) { results { name } }
      }
    """
    with CaptureQueriesContext(connection) as pag_ctx:
        pag_res = schema.execute_sync(paginated_query, variable_values=variables)
    assert pag_res.errors is None
    pag_sql = next(
        q["sql"]
        for q in pag_ctx.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT") and "tests_group" in q["sql"]
    )
    pag_joins = pag_sql.upper().count(" JOIN ")

    assert pag_joins == list_joins, (
        f"OffsetPaginated query has {pag_joins} JOINs but the equivalent list "
        f"query has {list_joins}; the relation filter is being applied twice.\n"
        f"paginated SQL: {pag_sql}"
    )


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_runs_perms_optimizer_and_type_hook_once(mocker):
    """An OffsetPaginated resolution must run the get_queryset pipeline once.

    The extension forwards filters/order/pagination to the inner resolver (#854),
    which already runs ``get_queryset_hook`` -> ``get_queryset``. The extension
    must not call ``get_queryset`` a second time, otherwise permission filtering
    (``filter_with_perms``) and the optimizer pass silently run twice (and
    relation filters duplicate their JOINs). The type-level ``get_queryset`` hook
    is guarded by ``type_get_queryset_did_run`` and runs once regardless.
    """
    type_get_queryset_calls = 0

    @strawberry_django.filter_type(models.Fruit, lookups=True)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class Fruit:
        id: int
        name: str

        @classmethod
        def get_queryset(cls, queryset, info, **kwargs):
            nonlocal type_get_queryset_calls
            type_get_queryset_calls += 1
            return queryset

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated(
            filters=FruitFilter
        )

    perms_spy = mocker.spy(field_mod, "filter_with_perms")
    optimize_spy = mocker.spy(DjangoOptimizerExtension, "optimize")

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension()])
    models.Fruit.objects.create(name="Apple")

    res = schema.execute_sync(
        "query ($f: FruitFilter){ fruits(filters: $f){ results { name } } }",
        variable_values={"f": {"name": {"exact": "Apple"}}},
    )

    assert res.errors is None
    assert perms_spy.call_count == 1  # was 2 before the fix
    assert optimize_spy.call_count == 1  # was 2 before the fix
    assert type_get_queryset_calls == 1  # guarded by type_get_queryset_did_run


@pytest.mark.django_db(transaction=True)
async def test_offset_paginated_applies_filter_pipeline_only_once_async():
    """Async variant of ``test_offset_paginated_applies_filter_pipeline_only_once``.

    Exercises the awaitable branch of ``StrawberryOffsetPaginatedExtension.resolve``;
    the filter pipeline must still run exactly once.
    """
    call_count = 0

    @strawberry_django.filter_type(models.Fruit)
    class FruitFilter:
        @strawberry_django.filter_field
        def name_contains(self, queryset, value: str, prefix: str):
            nonlocal call_count
            call_count += 1
            return queryset, Q(**{f"{prefix}name__icontains": value})

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class Fruit:
        id: int
        name: str

    @strawberry.type
    class Query:
        fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated(
            filters=FruitFilter
        )

    schema = strawberry.Schema(query=Query)
    await models.Fruit.objects.acreate(name="Apple")

    query = """
      query ($filters: FruitFilter) {
        fruits(filters: $filters) {
          results { name }
        }
      }
    """
    res = await schema.execute(
        query, variable_values={"filters": {"nameContains": "App"}}
    )

    assert res.errors is None
    assert res.data == {"fruits": {"results": [{"name": "Apple"}]}}
    assert call_count == 1, (
        f"filter pipeline ran {call_count} times for a single async OffsetPaginated "
        "resolution (expected 1); it is being applied twice"
    )


@pytest.mark.django_db(transaction=True)
def test_offset_paginated_does_not_duplicate_joins_with_or_across_relations():
    """OR across two multivalued relations + DISTINCT must not double the JOINs.

    Mirrors the query shape that originally surfaced the double-filter bug: an
    ``OR`` spanning two multivalued relations with ``DISTINCT``. The paginated
    field must emit the same JOINs as the equivalent non-paginated list field;
    the bug applied the filter twice, joining each relation twice and squaring
    the row count.
    """

    @strawberry_django.filter_type(models.Tag, lookups=True)
    class TagFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(models.User, lookups=True)
    class UserFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(models.Group, lookups=True)
    class GroupFilter:
        name: strawberry.auto
        tags: TagFilter | None
        users: UserFilter | None

    @strawberry_django.type(models.Group, filters=GroupFilter)
    class GroupType:
        id: int
        name: str

    @strawberry.type
    class Query:
        groups_paginated: OffsetPaginated[GroupType] = (
            strawberry_django.offset_paginated(filters=GroupFilter)
        )
        groups_list: list[GroupType] = strawberry_django.field(filters=GroupFilter)

    schema = strawberry.Schema(query=Query)
    group = models.Group.objects.create(name="g1")
    tag = models.Tag.objects.create(name="t1")
    group.tags.add(tag)
    models.User.objects.create(name="u1", group=group)

    variables = {
        "filters": {
            "tags": {"name": {"exact": "t1"}},
            "OR": {"users": {"name": {"exact": "u1"}}},
            "DISTINCT": True,
        }
    }

    list_query = """
      query ($filters: GroupFilter) {
        groupsList(filters: $filters) { name }
      }
    """
    with CaptureQueriesContext(connection) as list_ctx:
        list_res = schema.execute_sync(list_query, variable_values=variables)
    assert list_res.errors is None
    list_sql = next(
        q["sql"]
        for q in list_ctx.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT") and "tests_group" in q["sql"]
    )
    list_joins = list_sql.upper().count(" JOIN ")

    paginated_query = """
      query ($filters: GroupFilter) {
        groupsPaginated(filters: $filters) { results { name } }
      }
    """
    with CaptureQueriesContext(connection) as pag_ctx:
        pag_res = schema.execute_sync(paginated_query, variable_values=variables)
    assert pag_res.errors is None
    pag_sql = next(
        q["sql"]
        for q in pag_ctx.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT") and "tests_group" in q["sql"]
    )
    pag_joins = pag_sql.upper().count(" JOIN ")

    assert pag_joins == list_joins, (
        f"OffsetPaginated query has {pag_joins} JOINs but the equivalent list "
        f"query has {list_joins}; the OR/relation filter is being applied twice.\n"
        f"paginated SQL: {pag_sql}"
    )
