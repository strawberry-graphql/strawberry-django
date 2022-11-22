from typing import List

import pytest
import strawberry
from django.conf import settings
from strawberry import auto

import strawberry_django
from strawberry_django import mutations

from .. import models, utils
from ..types import (
    Color,
    ColorInput,
    ColorPartialInput,
    Fruit,
    FruitInput,
    FruitPartialInput,
    FruitType,
    FruitTypeInput,
    FruitTypePartialInput,
)


@strawberry_django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto


@strawberry.type
class Mutation:
    createFruit: Fruit = mutations.create(FruitInput)
    createFruits: List[Fruit] = mutations.create(FruitInput)
    updateFruits: List[Fruit] = mutations.update(FruitPartialInput, filters=FruitFilter)
    deleteFruits: List[Fruit] = mutations.delete(filters=FruitFilter)

    createColor: Color = mutations.create(ColorInput)
    createColors: List[Color] = mutations.create(ColorInput)
    updateColors: List[Color] = mutations.update(ColorPartialInput)
    deleteColors: List[Color] = mutations.delete()

    createFruitType: FruitType = mutations.create(FruitTypeInput)
    createFruitTypes: List[FruitType] = mutations.create(FruitTypeInput)
    updateFruitTypes: List[FruitType] = mutations.update(FruitTypePartialInput)
    deleteFruitTypes: List[FruitType] = mutations.delete()


@pytest.fixture
def mutation(db):
    mutation = Mutation

    if settings.GEOS_IMPORTED:
        from ..types import GeoField, GeoFieldInput, GeoFieldPartialInput

        @strawberry.type
        class GeoMutation(Mutation):
            createGeoField: GeoField = mutations.create(GeoFieldInput)
            updateGeoFields: List[GeoField] = mutations.update(GeoFieldPartialInput)

        mutation = GeoMutation

    return utils.generate_query(mutation=mutation)
