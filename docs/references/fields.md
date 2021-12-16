# Fields

Fields can be defined manually or `auto` type can be used for automatic type resolution. All basic field types and relation fields are supported out of the box.

```python
import strawberry
from strawberry.django import auto

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
