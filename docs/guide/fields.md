---
title: Defining Fields
---

# Defining Fields

> [!TIP]
> It is highly recommended to enable the [Query Optimizer Extension](optimizer.md)
> for improved performance and avoid some common pitfalls (e.g. the `n+1` issue)

Fields can be defined manually or `auto` type can be used for automatic type resolution. All basic field types and relation fields are supported out of the box. If you use a library that defines a custom field you will need to define an equivalent type such as `str`, `float`, `bool`, `int` or `id`.

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto

# equivalent type, inferred by `strawberry`

@strawberry_django.type(models.Fruit)
class Fruit2:
    id: strawberry.ID
    name: str
```

> [!TIP]
> For choices using
> [Django's TextChoices/IntegerChoices](https://docs.djangoproject.com/en/4.2/ref/models/fields/#enumeration-types)
> it is recommented using the [django-choices-field](../integrations/choices-field.md) integration
> enum handling.

## Relationships

All one-to-one, one-to-many, many-to-one and many-to-many relationship types are supported, and the many-to-many relation is described using the `typing.List` annotation.
The default resolver of `strawberry_django.fields()` resolves the relationship based on given type information.

```python title="types.py"
from typing import List

@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: "Color"


@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]
```

Note that all relations can naturally trigger the n+1 problem. To avoid that, you can either
enable the [Optimizer Extension](./optimizer.md) which will automatically
solve some general issues for you, or even use
[Data Loaders](https://strawberry.rocks/docs/guides/dataloaders) for more complex
situations.

## Field customization

All Django types are encoded using the `strawberry_django.field()` field type by default. Fields can be customized with various parameters.

```python title="types.py"
@strawberry_django.type(models.Color)
class Color:
    another_name: auto = strawberry_django.field(field_name='name')
    internal_name: auto = strawberry_django.field(
        name='fruits',
        field_name='fruit_set',
        filters=FruitFilter,
        order=FruitOrder,
        pagination=True,
        description="A list of fruits with this color"
    )
```

## Defining types for auto fields

When using `strawberry.auto` to resolve a field's type, Strawberry Django uses a dict that maps
each django field field type to its proper type. e.g.:

```python
{
    models.CharField: str,
    models.IntegerField: int,
    ...,
}
```

If you are using a custom django field that is not part of the default library,
or you want to use a different type for a field, you can do that by overriding
its value in the map, like:

```python
from typing import NewType

from django.db import models
import strawberry
import strawberry_django
from strawberry_django.fields.types import field_type_map

Slug = strawberry.scalar(
    NewType("Slug", str),
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

@strawberry_django.type
class MyCustomFileType:
    ...

field_type_map.update({
    models.SlugField: Slug,
    models.FileField: MyCustomFileType,
})
```

## Including / excluding Django model fields by name

> [!WARNING]
> These new keywords should be used with caution, as they may inadvertently lead to exposure of unwanted data. Especially with `fields="__all__"` or `exclude`, sensitive model attributes may be included and made available in the schema without your awareness.

`strawberry_django.type` includes two optional keyword fields to help you populate fields from the Django model, `fields` and `exclude`.

Valid values for `fields` are:

- `__all__` to assign `strawberry.auto` as the field type for all model fields.
- `[<List of field names>]` to assign `strawberry.auto` as the field type for the enumerated fields. These can be combined with manual type annotations if needed.

```python title="All Fields"
@strawberry_django.type(models.Fruit, fields="__all__")
class FruitType:
    pass
```

```python title="Enumerated Fields"
@strawberry_django.type(models.Fruit, fields=["name", "color"])
class FruitType:
    pass
```

```python title="Overriden Fields"
@strawberry_django.type(models.Fruit, fields=["color"])
class FruitType:
    name: str
```

Valid values for `exclude` are:

- `[<List of field names>]` to exclude from the fields list. All other Django model fields will included and have `strawberry.auto` as the field type. These can also be overriden if another field type should be assigned. An empty list is ignored.

```python title="Exclude Fields"
@strawberry_django.type(models.Fruit, exclude=["name"])
class FruitType:
    pass
```

```python title="Overriden Exclude Fields"
@strawberry_django.type(models.Fruit, exclude=["name"])
class FruitType:
    color: int
```

Note that `fields` has precedence over `exclude`, so if both are provided, then `exclude` is ignored.

## Overriding the field class (advanced)

If in your project, you want to change/add some of the standard `strawberry_django.field()` behaviour,
it is possible to use your own custom field class when decorating a `strawberry_django.type` with the `field_cls` argument, e.g.

```python title="types.py"
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
