import pytest
import strawberry
import strawberry_django
from .. import models
from .. import types
from .. import utils
from .. types import (
    Fruit, FruitInput, FruitPartialInput,
    Color, ColorInput, ColorPartialInput,
    FruitType, FruitTypeInput, FruitTypePartialInput,
)
from strawberry_django import auto, mutations
from typing import List

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

    createFruitType: FruitType= mutations.create(FruitTypeInput)
    createFruitTypes: List[FruitType] = mutations.create(FruitTypeInput)
    updateFruitTypes: List[FruitType] = mutations.update(FruitTypePartialInput)
    deleteFruitTypes: List[FruitType] = mutations.delete()

@pytest.fixture
def mutation(db):
    return utils.generate_query(mutation=Mutation)
