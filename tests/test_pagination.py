from typing import List

import pytest
import strawberry
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation

import strawberry_django
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


@strawberry_django.type(models.Group, pagination=True)
class Group:
    name: auto


@strawberry_django.type(models.User)
class User:
    name: auto
    group: Group


@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field()
    berries: List[BerryFruit] = strawberry_django.field()
    users: List[User] = strawberry_django.field()
    groups: List[Group] = strawberry_django.field()


@pytest.fixture
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
    from strawberry_django.pagination import OffsetPaginationInput

    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(pagination: OffsetPaginationInput) -> List[Fruit]:
            queryset = models.Fruit.objects.all()
            return strawberry_django.pagination.apply(pagination, queryset)

    query = utils.generate_query(Query)
    result = query("{ fruits(pagination: { limit: 1 }) { id name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]


def test_pagination_on_related_field_definition():
    from strawberry_django.fields.field import StrawberryDjangoField

    group_field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(List[Group])
    )
    assert group_field.get_pagination() is not None
    assert User._type_definition.get_field("group").get_pagination() is None
