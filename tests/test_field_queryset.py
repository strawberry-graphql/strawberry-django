import pytest
import strawberry
from asgiref.sync import sync_to_async
from strawberry import auto, relay

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import DjangoListConnection

from . import models, utils


@strawberry_django.filter_type(models.Fruit, lookups=True)
class FruitFilter:
    name: auto


@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    id: auto
    name: auto
    sweetness: auto


@strawberry_django.type(models.Fruit, filters=FruitFilter)
class FruitNode(relay.Node):
    name: auto


@strawberry_django.type(models.Fruit)
class BerryFruit:
    name: auto

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return queryset.filter(name__endswith="berry")


@strawberry.type
class Query:
    sweet_fruits: list[Fruit] = strawberry_django.field(
        queryset=models.Fruit.objects.filter(sweetness__gte=5),
    )
    sweet_fruits_by_name: list[Fruit] = strawberry_django.field(
        queryset=models.Fruit.objects.filter(sweetness__gte=5).order_by("name"),
    )
    sweet_fruit: Fruit | None = strawberry_django.field(
        queryset=models.Fruit.objects.filter(sweetness__gte=5),
    )
    sweet_fruits_paginated: OffsetPaginated[Fruit] = strawberry_django.offset_paginated(
        queryset=models.Fruit.objects.filter(sweetness__gte=5),
    )
    sweet_fruits_connection: DjangoListConnection[FruitNode] = (
        strawberry_django.connection(
            queryset=models.Fruit.objects.filter(sweetness__gte=5),
        )
    )
    sweet_berries: list[BerryFruit] = strawberry_django.field(
        queryset=models.Fruit.objects.filter(sweetness__gte=5),
    )


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(params=["sync", "async", "sync_no_optimizer", "async_no_optimizer"])
def query(request):
    extensions = (
        [] if request.param.endswith("_no_optimizer") else [DjangoOptimizerExtension]
    )
    schema = strawberry.Schema(query=Query, extensions=extensions)

    async def execute(query: str, variable_values: dict | None = None):
        if request.param.startswith("async"):
            return await schema.execute(query, variable_values=variable_values)

        return await sync_to_async(schema.execute_sync)(
            query, variable_values=variable_values
        )

    return execute


@pytest.fixture
def sweet_fruits(db):
    return [
        models.Fruit.objects.create(name="strawberry", sweetness=8),
        models.Fruit.objects.create(name="lemon", sweetness=1),
        models.Fruit.objects.create(name="banana", sweetness=6),
        models.Fruit.objects.create(name="raspberry", sweetness=5),
    ]


async def test_queryset_list(query, sweet_fruits):
    result = await query("{ sweetFruits { name } }")

    assert not result.errors
    assert result.data == {
        "sweetFruits": [
            {"name": "strawberry"},
            {"name": "banana"},
            {"name": "raspberry"},
        ],
    }


async def test_queryset_list_with_filters(query, sweet_fruits):
    result = await query(
        '{ sweetFruits(filters: { name: { contains: "berry" } }) { name } }'
    )

    assert not result.errors
    assert result.data == {
        "sweetFruits": [{"name": "strawberry"}, {"name": "raspberry"}],
    }


async def test_queryset_list_with_type_get_queryset(query, sweet_fruits):
    result = await query("{ sweetBerries { name } }")

    assert not result.errors
    assert result.data == {
        "sweetBerries": [{"name": "strawberry"}, {"name": "raspberry"}],
    }


async def test_queryset_single(query, sweet_fruits):
    strawberry_, lemon, *_ = sweet_fruits

    result = await query(
        """
        query GetFruit($pk: ID!) {
          sweetFruit(pk: $pk) {
            name
          }
        }
        """,
        {"pk": strawberry_.pk},
    )

    assert not result.errors
    assert result.data == {"sweetFruit": {"name": "strawberry"}}

    # The lemon exists, but is not part of the field's queryset
    result = await query(
        """
        query GetFruit($pk: ID!) {
          sweetFruit(pk: $pk) {
            name
          }
        }
        """,
        {"pk": lemon.pk},
    )

    assert not result.errors
    assert result.data == {"sweetFruit": None}


async def test_queryset_offset_paginated(query, sweet_fruits):
    result = await query(
        """
        query {
          sweetFruitsPaginated(pagination: { limit: 2 }) {
            totalCount
            results {
              name
            }
          }
        }
        """
    )

    assert not result.errors
    assert result.data == {
        "sweetFruitsPaginated": {
            "totalCount": 3,
            "results": [{"name": "strawberry"}, {"name": "banana"}],
        },
    }


async def test_queryset_connection(query, sweet_fruits):
    result = await query(
        """
        query {
          sweetFruitsConnection(
            first: 1
            filters: { name: { contains: "berry" } }
          ) {
            totalCount
            edges {
              node {
                name
              }
            }
          }
        }
        """
    )

    assert not result.errors
    assert result.data == {
        "sweetFruitsConnection": {
            "totalCount": 2,
            "edges": [{"node": {"name": "strawberry"}}],
        },
    }


async def test_queryset_is_not_cached_between_executions(query, sweet_fruits):
    # The queryset is ordered, so it is not cloned to order it by its pk
    result = await query("{ sweetFruitsByName { name } }")

    assert not result.errors
    assert result.data == {
        "sweetFruitsByName": [
            {"name": "banana"},
            {"name": "raspberry"},
            {"name": "strawberry"},
        ],
    }

    await models.Fruit.objects.acreate(name="mango", sweetness=9)
    await models.Fruit.objects.filter(name="banana").aupdate(sweetness=2)

    result = await query("{ sweetFruitsByName { name } }")

    assert not result.errors
    assert result.data == {
        "sweetFruitsByName": [
            {"name": "mango"},
            {"name": "raspberry"},
            {"name": "strawberry"},
        ],
    }


def test_queryset_with_optimizer_runs_a_single_query(sweet_fruits):
    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    with utils.assert_num_queries(1):
        result = schema.execute_sync("{ sweetFruits { name } }")

    assert not result.errors
    assert result.data == {
        "sweetFruits": [
            {"name": "strawberry"},
            {"name": "banana"},
            {"name": "raspberry"},
        ],
    }


def test_queryset_with_resolver_raises():
    def resolver() -> list[Fruit]:
        return models.Fruit.objects.all()  # type: ignore

    with pytest.raises(TypeError, match="cannot have both a `queryset` and a resolver"):
        strawberry_django.field(  # type: ignore
            resolver=resolver,
            queryset=models.Fruit.objects.all(),
        )

    with pytest.raises(TypeError, match="cannot have both a `queryset` and a resolver"):

        @strawberry.type
        class ResolverQuery:
            @strawberry_django.field(queryset=models.Fruit.objects.all())
            def fruits(self) -> list[Fruit]:
                return models.Fruit.objects.all()  # type: ignore

    with pytest.raises(TypeError, match="cannot have both a `queryset` and a resolver"):
        strawberry_django.connection(
            resolver=resolver,
            queryset=models.Fruit.objects.all(),
        )


def test_queryset_on_django_type_field_raises():
    with pytest.raises(
        TypeError,
        match='Field "fruits" on type "Color" cannot define a `queryset`',
    ):

        @strawberry_django.type(models.Color)
        class Color:
            fruits: list[Fruit] = strawberry_django.field(
                queryset=models.Fruit.objects.filter(sweetness__gte=5),
            )
