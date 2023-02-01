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
    create_fruit: Fruit = mutations.create(FruitInput)
    create_fruits: List[Fruit] = mutations.create(FruitInput)
    update_fruits: List[Fruit] = mutations.update(
        FruitPartialInput, filters=FruitFilter
    )
    delete_fruits: List[Fruit] = mutations.delete(filters=FruitFilter)

    create_color: Color = mutations.create(ColorInput)
    create_colors: List[Color] = mutations.create(ColorInput)
    update_colors: List[Color] = mutations.update(ColorPartialInput)
    delete_colors: List[Color] = mutations.delete()

    create_fruit_type: FruitType = mutations.create(FruitTypeInput)
    create_fruit_types: List[FruitType] = mutations.create(FruitTypeInput)
    update_fruit_types: List[FruitType] = mutations.update(FruitTypePartialInput)
    delete_fruit_types: List[FruitType] = mutations.delete()


@pytest.fixture
def mutation(db):
    if settings.GEOS_IMPORTED:
        from ..types import GeoField, GeoFieldInput, GeoFieldPartialInput

        @strawberry.type
        class GeoMutation(Mutation):
            create_geo_field: GeoField = mutations.create(GeoFieldInput)
            update_geo_fields: List[GeoField] = mutations.update(GeoFieldPartialInput)

        mutation = GeoMutation

    else:
        mutation = Mutation

    return utils.generate_query(mutation=mutation)
