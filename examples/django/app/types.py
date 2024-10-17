from typing import Optional

from strawberry import auto

import strawberry_django
from django.contrib.auth import get_user_model
from django.db.models import Q

from . import models

# filters


@strawberry_django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
    color: Optional["ColorFilter"]

    @strawberry_django.filter_field
    def special_filter(self, prefix: str, value: str):
        return Q(**{f"{prefix}name": value})


@strawberry_django.filters.filter(models.Color, lookups=True)
class ColorFilter:
    id: auto
    name: auto
    fruits: Optional[FruitFilter]

    @strawberry_django.filter_field
    def filter(self, prefix, queryset):
        return queryset, Q()


# order


@strawberry_django.ordering.order(models.Fruit)
class FruitOrder:
    name: auto
    color: Optional["ColorOrder"]


@strawberry_django.ordering.order(models.Color)
class ColorOrder:
    name: auto
    fruits: FruitOrder

    @strawberry_django.order_field
    def special_order(self, prefix: str, value: auto):
        return [value.resolve(f"{prefix}fruits__name")]


# types


@strawberry_django.type(
    models.Fruit,
    filters=FruitFilter,
    order=FruitOrder,
    pagination=True,
)
class Fruit:
    id: auto
    name: auto
    color: Optional["Color"]


@strawberry_django.type(
    models.Color,
    filters=ColorFilter,
    order=ColorOrder,
    pagination=True,
)
class Color:
    id: auto
    name: auto
    fruits: list[Fruit]


@strawberry_django.type(get_user_model())
class User:
    id: auto
    username: auto
    password: auto
    email: auto


# input types


@strawberry_django.input(models.Fruit)
class FruitInput:
    id: auto
    name: auto
    color: auto


@strawberry_django.input(models.Color)
class ColorInput:
    id: auto
    name: auto
    fruits: auto


@strawberry_django.input(get_user_model())
class UserInput:
    username: auto
    password: auto
    email: auto


# partial input types


@strawberry_django.input(models.Fruit, partial=True)
class FruitPartialInput(FruitInput):
    pass


@strawberry_django.input(models.Color, partial=True)
class ColorPartialInput(ColorInput):
    pass
