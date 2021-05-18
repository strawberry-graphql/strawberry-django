import pytest
import strawberry
import strawberry_django
from strawberry_django import auto
from typing import List

from tests import utils, models

@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto

@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry_django.field()

@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_pagination(query, fruits):
    result = query('{ fruits(pagination: { offset: 1, limit:1 }) { name } }')
    assert not result.errors
    assert result.data['fruits'] == [
        { 'name': 'raspberry'},
    ]
