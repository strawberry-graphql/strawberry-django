from typing import cast

import pytest
import strawberry
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from strawberry import auto

import strawberry_django
from strawberry_django import mutations
from strawberry_django.mutations import resolvers
from tests import models, utils
from tests.types import (
    Color,
    ColorInput,
    ColorPartialInput,
    Fruit,
    FruitInput,
    FruitPartialInput,
    FruitType,
    FruitTypeInput,
    FruitTypePartialInput,
    TomatoWithRequiredPictureInput,
    TomatoWithRequiredPicturePartialInput,
    TomatoWithRequiredPictureType,
)


@strawberry_django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto


@strawberry.type
class Mutation:
    create_fruit: Fruit = mutations.create(FruitInput)
    create_fruits: list[Fruit] = mutations.create(FruitInput)
    update_fruits: list[Fruit] = mutations.update(
        FruitPartialInput, filters=FruitFilter, key_attr="id"
    )
    create_tomato_with_required_picture: TomatoWithRequiredPictureType = (
        mutations.create(TomatoWithRequiredPictureInput)
    )
    update_tomato_with_required_picture: TomatoWithRequiredPictureType = (
        mutations.update(TomatoWithRequiredPicturePartialInput)
    )

    @strawberry_django.mutation
    def update_lazy_fruit(self, info, data: FruitPartialInput) -> Fruit:
        fruit = SimpleLazyObject(models.Fruit.objects.get)
        return cast(
            "Fruit",
            resolvers.update(
                info,
                fruit,
                resolvers.parse_input(info, vars(data), key_attr="id"),
                key_attr="id",
            ),
        )

    @strawberry_django.mutation
    def delete_lazy_fruit(self, info) -> Fruit:
        fruit = SimpleLazyObject(models.Fruit.objects.get)
        return cast(
            "Fruit",
            resolvers.delete(
                info,
                fruit,
            ),
        )

    delete_fruits: list[Fruit] = mutations.delete(filters=FruitFilter)

    create_color: Color = mutations.create(ColorInput)
    create_colors: list[Color] = mutations.create(ColorInput)
    update_colors: list[Color] = mutations.update(ColorPartialInput)
    delete_colors: list[Color] = mutations.delete()

    create_fruit_type: FruitType = mutations.create(FruitTypeInput)
    create_fruit_types: list[FruitType] = mutations.create(FruitTypeInput)
    update_fruit_types: list[FruitType] = mutations.update(FruitTypePartialInput)
    delete_fruit_types: list[FruitType] = mutations.delete()


@pytest.fixture
def mutation(db):
    if settings.GEOS_IMPORTED:
        from tests.types import GeoField, GeoFieldInput, GeoFieldPartialInput

        @strawberry.type
        class GeoMutation(Mutation):
            create_geo_field: GeoField = mutations.create(GeoFieldInput)
            update_geo_fields: list[GeoField] = mutations.update(GeoFieldPartialInput)

        mutation = GeoMutation

    else:
        mutation = Mutation

    return utils.generate_query(mutation=mutation)


@pytest.fixture
def fruit(db):
    return models.Fruit.objects.create(name="Strawberry")
