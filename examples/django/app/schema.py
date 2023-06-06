from typing import List

import strawberry

import strawberry_django
from strawberry_django import auth, mutations

from .types import (
    Color,
    ColorInput,
    ColorPartialInput,
    Fruit,
    FruitInput,
    FruitPartialInput,
    User,
    UserInput,
)


@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field()
    fruits: List[Fruit] = strawberry_django.field()

    color: Color = strawberry_django.field()
    colors: List[Color] = strawberry_django.field()


@strawberry.type
class Mutation:
    create_fruit: Fruit = mutations.create(FruitInput)
    create_fruits: List[Fruit] = mutations.create(FruitInput)
    update_fruits: List[Fruit] = mutations.update(FruitPartialInput)
    delete_fruits: List[Fruit] = mutations.delete()

    create_color: Color = mutations.create(ColorInput)
    create_colors: List[Color] = mutations.create(ColorInput)
    update_colors: List[Color] = mutations.update(ColorPartialInput)
    delete_colors: List[Color] = mutations.delete()

    register: User = auth.register(UserInput)


schema = strawberry.Schema(query=Query, mutation=Mutation)
