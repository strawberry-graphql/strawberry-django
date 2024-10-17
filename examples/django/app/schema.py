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
    fruits: list[Fruit] = strawberry_django.field()

    color: Color = strawberry_django.field()
    colors: list[Color] = strawberry_django.field()


@strawberry.type
class Mutation:
    create_fruit: Fruit = mutations.create(FruitInput)
    create_fruits: list[Fruit] = mutations.create(FruitInput)
    update_fruits: list[Fruit] = mutations.update(FruitPartialInput)
    delete_fruits: list[Fruit] = mutations.delete()

    create_color: Color = mutations.create(ColorInput)
    create_colors: list[Color] = mutations.create(ColorInput)
    update_colors: list[Color] = mutations.update(ColorPartialInput)
    delete_colors: list[Color] = mutations.delete()

    register: User = auth.register(UserInput)


schema = strawberry.Schema(query=Query, mutation=Mutation)
