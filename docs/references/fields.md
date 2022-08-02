# Fields

Fields can be defined manually or `auto` type can be used for automatic type resolution. All basic field types and relation fields are supported out of the box. If you use a library that designates a custom field you will need to define an equivalent type such as `str`, `float`, `bool`, `int` or `id`

```python
#types.py

import strawberry
from strawberry import auto

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto

# equivalent type

@strawberry.django.type(models.Fruit)
class Fruit:
    id: strawberry.ID
    name: str
```

## Relationships

All one to one, one to many, many to one and many to many relationship types are supported. `typing.List` is used for many relationship. Default resolver of `strawberry.django.fields()` resolves the relationship based on given type information.

```python
#types.py

from typing import List

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: 'Color'

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]
```

## Field customization

All django types are using `strawberry.django.field()` field type by default. Fields can be customized with various parameters.

```python
#types.py

@strawberry.django.type(models.Color)
class Color:
    another_name: auto = strawberry.django.field(field_name='name')
    internal_name: auto = strawberry.django.field(
        name='fruits',
        field_name='fruit_set',
        filters=FruitFilter,
        order=FruitOrder,
        pagination=True
    )
```

## Overriding the field class (advanced)

If in your project, you want to change/add some of the standard `strawberry.django.field()` behaviour, it is possible to use your own custom field class when decorating a `strawberry.django.type` with the `field_cls` argument, e.g.

```python
class CustomStrawberryDjangoField(StrawberryDjangoField):
    """Your custom behaviour goes here."""

@strawberry_django.type(User, field_cls=CustomStrawberryDjangoField)
class UserType:
    # Each of these fields will be an instance of `CustomStrawberryDjangoField`.
    id: int
    name: auto


@strawberry.type
class UserQuery:
    # You can directly create your custom field class on a plain strawberry type
    user: UserType = CustomStrawberryDjangoField()

```

In this example, each of the fields of the `UserType` will be automatically created by `CustomStrawberryDjangoField`,
which may implement anything from custom pagination of relationships to altering the field permissions.
