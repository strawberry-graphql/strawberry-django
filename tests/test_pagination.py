from typing import List, cast

import pytest
import strawberry
from strawberry import auto
from strawberry.types import ExecutionResult

import strawberry_django
from strawberry_django.pagination import OffsetPaginationInput, apply
from tests import models, utils


@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit, pagination=True)
class BerryFruit:
    name: auto

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return queryset.filter(name__contains="berry")


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field()
    berries: List[BerryFruit] = strawberry_django.field()


@pytest.fixture()
def query():
    return utils.generate_query(Query)


def test_pagination(query, fruits):
    result = query("{ fruits(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"name": "raspberry"},
    ]


def test_pagination_of_filtered_query(query, fruits):
    result = query("{ berries(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["berries"] == [
        {"name": "raspberry"},
    ]


def test_resolver_pagination(fruits):
    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(self, pagination: OffsetPaginationInput) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return cast(List[Fruit], apply(pagination, queryset))

    query = utils.generate_query(Query)
    result = query("{ fruits(pagination: { limit: 1 }) { id name } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]
