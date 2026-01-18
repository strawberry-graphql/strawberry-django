import textwrap
from typing import Annotated

import pytest
import strawberry
from django.db.models import QuerySet
from django.test.utils import override_settings

import strawberry_django
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
            -5,
        ),  # Negative limit without max passes through (unlimited in practice)
        (
            -5,
            None,
            None,
            -5,
        ),  # Negative limit without settings passes through (unlimited in practice)
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
