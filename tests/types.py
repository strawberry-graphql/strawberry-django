from typing import List

import strawberry_django
from strawberry_django import auto

from . import models


@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: "Color"
    types: List["FruitType"]


@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]


@strawberry_django.type(models.FruitType)
class FruitType:
    id: auto
    name: auto
    fruits: List[Fruit]


@strawberry_django.input(models.Fruit)
class FruitInput(Fruit):
    pass


@strawberry_django.input(models.Color)
class ColorInput(Color):
    pass


@strawberry_django.input(models.FruitType)
class FruitTypeInput(FruitType):
    pass


@strawberry_django.input(models.Fruit, partial=True)
class FruitPartialInput(FruitInput):
    pass


@strawberry_django.input(models.Color, partial=True)
class ColorPartialInput(ColorInput):
    pass


@strawberry_django.input(models.FruitType, partial=True)
class FruitTypePartialInput(FruitTypeInput):
    pass


@strawberry_django.type(models.User)
class User:
    id: auto
    name: auto
    group: "Group"
    tag: "Tag"


@strawberry_django.type(models.Group)
class Group:
    id: auto
    name: auto
    tags: List["Tag"]
    users: List[User]


@strawberry_django.type(models.Tag)
class Tag:
    id: auto
    name: auto
    groups: List[Group]
    user: User
