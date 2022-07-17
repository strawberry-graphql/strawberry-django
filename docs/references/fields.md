# Fields

Fields can be defined manually or `auto` type can be used for automatic type resolution. All basic field types and relation fields are supported out of the box. If you use a library that defines a custom field you will need to define an equivalent type such as `str`, `float`, `bool`, `int` or `id`.

```python
# types.py
import strawberry
from strawberry import auto

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto

# equivalent type, inferred by `strawberry`

@strawberry.django.type(models.Fruit)
class Fruit:
    id: strawberry.ID
    name: str
```
# Choice fields
For IntegerChoices Enum can be used to display the value

```python
# models.py
class FruitColor(models.IntegerChoices):
  Red = 1
  Yellow = 2
  Green = 3

# types.py
from enum import Enum

@strawberry.enum
class FruitColor(Enum):
  Red = 1
  Yellow = 2
  Green = 3
  
@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: FruitColor
```

## Relationships

All one-to-one, one-to-many, many-to-one and many-to-many relationship types are supported, and the many-to-many relation is described using the `typing.List` annotation.
The default resolver of `strawberry.django.fields()` resolves the relationship based on given type information.

```python
# types.py
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

All Django types are encoded using the `strawberry.django.field()` field type by default. Fields can be customized with various parameters.

```python
# types.py
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
