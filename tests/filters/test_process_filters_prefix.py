from typing import cast

import pytest
import strawberry
from django.db.models import CharField, Q, QuerySet, Value
from django.db.models.functions import Concat
from strawberry import auto

import strawberry_django
from strawberry_django.fields import filter_types
from strawberry_django.filters import process_filters
from tests import models


def test_process_filters_prefix(db):
    @strawberry_django.filter_type(models.Vegetable)
    class VegetableFilter:
        name: auto

        @strawberry_django.filter_field
        def name_and_description(
            self,
            info: strawberry.Info,
            queryset: QuerySet,
            value: filter_types.StrFilterLookup[str],
            prefix: str,
        ) -> tuple[QuerySet, Q]:
            queryset = queryset.alias(
                _name_description=Concat(
                    f"{prefix}name",
                    Value(" "),
                    f"{prefix}description",
                    output_field=CharField(),
                )
            )
            return process_filters(
                cast("WithStrawberryObjectDefinition", value),
                queryset,
                info,
                prefix="_name_description__",
            )

    @strawberry_django.type(models.Vegetable, filters=VegetableFilter)
    class VegetableType:
        id: auto
        name: auto

    @strawberry.type
    class Query:
        vegetables: list[VegetableType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    models.Vegetable.objects.create(
        name="carrot", description="orange root", world_production=40.0e6
    )
    result = schema.execute_sync("""
    {
        vegetables(filters: {
            nameAndDescription: { iContains: "orange" }
        }) { name }
    }
    """)
    assert not result.errors
    assert result.data == {"vegetables": [{"name": "carrot"}]}


def test_process_filters_prefix_missing_trailing_underscores(db):
    @strawberry_django.filter_type(models.Vegetable)
    class VegetableFilter:
        name: auto

        @strawberry_django.filter_field
        def name_and_description(
            self,
            info: strawberry.Info,
            queryset: QuerySet,
            value: filter_types.StrFilterLookup[str],
            prefix: str,
        ) -> tuple[QuerySet, Q]:
            queryset = queryset.alias(
                _name_description=Concat(
                    f"{prefix}name",
                    Value(" "),
                    f"{prefix}description",
                    output_field=CharField(),
                )
            )
            return process_filters(
                cast("WithStrawberryObjectDefinition", value),
                queryset,
                info,
                prefix="_name_description",
            )

    @strawberry_django.type(models.Vegetable, filters=VegetableFilter)
    class VegetableType:
        id: auto
        name: auto

    @strawberry.type
    class Query:
        vegetables: list[VegetableType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query)

    models.Vegetable.objects.create(
        name="carrot", description="orange root", world_production=40.0e6
    )
    with pytest.warns(UserWarning, match="does not end with '__'"):
        result = schema.execute_sync("""
        {
            vegetables(filters: {
                nameAndDescription: { iContains: "orange" }
            }) { name }
        }
        """)
    assert result.errors
