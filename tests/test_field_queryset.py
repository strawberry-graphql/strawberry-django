import dataclasses
import json

import pytest
import strawberry
from asgiref.sync import sync_to_async
from django.http import HttpRequest
from strawberry import auto, relay
from strawberry.django.views import GraphQLView

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


@strawberry_django.type(models.Color)
class Color:
    name: auto


@strawberry_django.type(models.Fruit)
class ColoredFruit:
    name: auto
    color: Color | None


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
    sweet_colored_fruits: list[ColoredFruit] = strawberry_django.field(
        queryset=models.Fruit.objects.filter(sweetness__gte=5),
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
        # Matches the filters and the type's `get_queryset` used by the tests,
        # but is not part of the fields' queryset
        models.Fruit.objects.create(name="blackberry", sweetness=3),
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
    color = models.Color.objects.create(name="red")
    models.Fruit.objects.filter(sweetness__gte=5).update(color=color)
    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    # Without the optimizer, the color of each fruit would be another query
    with utils.assert_num_queries(1):
        result = schema.execute_sync("{ sweetColoredFruits { name color { name } } }")

    assert not result.errors
    assert result.data == {
        "sweetColoredFruits": [
            {"name": "strawberry", "color": {"name": "red"}},
            {"name": "banana", "color": {"name": "red"}},
            {"name": "raspberry", "color": {"name": "red"}},
        ],
    }


def test_queryset_with_view_root_value(sweet_fruits, rf):
    @dataclasses.dataclass
    class Root:
        request: HttpRequest

    class View(GraphQLView):
        def get_root_value(self, request):
            return Root(request=request)

    view = View.as_view(schema=strawberry.Schema(query=Query))
    request = rf.post(
        "/graphql/",
        {"query": "{ sweetFruits { name } sweetFruitsConnection { totalCount } }"},
        content_type="application/json",
    )

    result = json.loads(view(request).content)

    assert "errors" not in result
    assert result["data"] == {
        "sweetFruits": [
            {"name": "strawberry"},
            {"name": "banana"},
            {"name": "raspberry"},
        ],
        "sweetFruitsConnection": {"totalCount": 3},
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
        strawberry_django.connection(  # type: ignore
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
