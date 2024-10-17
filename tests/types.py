from __future__ import annotations

from django.conf import settings
from strawberry import auto  # noqa: TCH002

import strawberry_django

from . import models


@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: Color | None
    types: list[FruitType]
    picture: auto


@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: list[Fruit]


@strawberry_django.type(models.FruitType)
class FruitType:
    id: auto
    name: auto
    fruits: list[Fruit]


@strawberry_django.type(models.TomatoWithRequiredPicture, fields="__all__")
class TomatoWithRequiredPictureType:
    pass


if settings.GEOS_IMPORTED:

    @strawberry_django.type(models.GeosFieldsModel)
    class GeoField:
        id: auto
        point: auto
        line_string: auto
        polygon: auto
        multi_point: auto
        multi_line_string: auto
        multi_polygon: auto

    @strawberry_django.input(models.GeosFieldsModel)
    class GeoFieldInput(GeoField):
        pass

    @strawberry_django.input(models.GeosFieldsModel, partial=True)
    class GeoFieldPartialInput(GeoField):
        pass


@strawberry_django.input(models.Fruit)
class FruitInput(Fruit):
    types: list[FruitTypeInput] | None  # type: ignore


@strawberry_django.input(models.TomatoWithRequiredPicture)
class TomatoWithRequiredPictureInput:
    id: auto
    name: auto


@strawberry_django.input(models.Color)
class ColorInput(Color):
    pass


@strawberry_django.input(models.FruitType)
class FruitTypeInput(FruitType):
    pass


@strawberry_django.input(models.Fruit, partial=True)
class FruitPartialInput(FruitInput):
    types: list[FruitTypePartialInput] | None  # type: ignore


@strawberry_django.partial(models.TomatoWithRequiredPicture, fields="__all__")
class TomatoWithRequiredPicturePartialInput(TomatoWithRequiredPictureType):
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
    group: Group
    tag: Tag


@strawberry_django.type(models.Group)
class Group:
    id: auto
    name: auto
    tags: list[Tag]
    users: list[User]


@strawberry_django.type(models.Tag)
class Tag:
    id: auto
    name: auto
    groups: list[Group]
    user: User
