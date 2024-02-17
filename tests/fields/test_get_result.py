from typing import List

import pytest
from django.db.models import QuerySet
from strawberry import relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.relay.types import ListConnection

from strawberry_django.fields.field import StrawberryDjangoField
from tests.types import FruitType


@pytest.mark.django_db()
def test_resolve_returns_queryset_with_fetched_results():
    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(List[FruitType]))
    result = field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is not None  # type: ignore


@pytest.mark.django_db()
async def test_resolve_returns_queryset_with_fetched_results_async():
    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(List[FruitType]))
    result = await field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is not None  # type: ignore


@pytest.mark.django_db()
def test_resolve_returns_queryset_without_fetching_results_when_disabling_it():
    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(List[FruitType]))
    field.disable_fetch_list_results = True
    result = field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is None  # type: ignore


@pytest.mark.django_db()
async def test_resolve_returns_queryset_without_fetching_results_when_disabling_it_async():
    field = StrawberryDjangoField(type_annotation=StrawberryAnnotation(List[FruitType]))
    field.disable_fetch_list_results = True
    result = await field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is None  # type: ignore


@pytest.mark.django_db()
def test_resolve_returns_queryset_without_fetching_results_for_connections():
    class FruitImplementingNode(relay.Node, FruitType): ...

    field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(ListConnection[FruitImplementingNode])
    )
    field.disable_fetch_list_results = True
    result = field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is None  # type: ignore


@pytest.mark.django_db()
async def test_resolve_returns_queryset_without_fetching_results_for_connections_async():
    class FruitImplementingNode(relay.Node, FruitType): ...

    field = StrawberryDjangoField(
        type_annotation=StrawberryAnnotation(ListConnection[FruitImplementingNode])
    )
    field.disable_fetch_list_results = True
    result = await field.get_result(None, None, [], {})
    assert isinstance(result, QuerySet)
    assert result._result_cache is None  # type: ignore
