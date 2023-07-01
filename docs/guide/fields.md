# Defining Fields

!!! tip

    It is highly recommended to enable the [Query Optimizer Extension](/guide/optimizer)
    for improved performance and avoid some common pitfalls (e.g. the `n+1` issue)

Fields can be defined manually or `auto` type can be used for automatic type resolution. All basic field types and relation fields are supported out of the box. If you use a library that defines a custom field you will need to define an equivalent type such as `str`, `float`, `bool`, `int` or `id`.

```{.python title=types.py}
import strawberry
from strawberry import auto

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto

# equivalent type, inferred by `strawberry`

@strawberry.django.type(models.Fruit)
class Fruit2:
    id: strawberry.ID
    name: str
```

!!! tip

    For choices using
    [Django's TextChoices/IntegerChoices](https://docs.djangoproject.com/en/4.2/ref/models/fields/#enumeration-types)
    it is recommented using the [django-choices-field](/integrations/choices-field) integration
    enum handling.

## Relationships

All one-to-one, one-to-many, many-to-one and many-to-many relationship types are supported, and the many-to-many relation is described using the `typing.List` annotation.
The default resolver of `strawberry.django.fields()` resolves the relationship based on given type information.

```{.python title=types.py}
from typing import List

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: "Color"


@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]
```

Note that all relations can naturally trigger the n+1 problem. To avoid that, you can either
enable the [Optimizer Extension](../optimizer) which will automatically
solve some general issues for you, or even use
[Data Loaders](https://strawberry.rocks/docs/guides/dataloaders) for more complex
situations.

## Field customization

All Django types are encoded using the `strawberry.django.field()` field type by default. Fields can be customized with various parameters.

```{.python title=types.py}
@strawberry.django.type(models.Color)
class Color:
    another_name: auto = strawberry.django.field(field_name='name')
    internal_name: auto = strawberry.django.field(
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

import strawberry
import strawberry_django

Slug = strawberry.scalar(
    NewType("Slug", str),
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

@strawberry.type
class MyCustomFileType:
    ...

strawberry_django.field_type_map.update({
    models.SlugField: Slug,
    models.FileField: MyCustomFileType,
})
```

## Overriding the field class (advanced)

If in your project, you want to change/add some of the standard `strawberry.django.field()` behaviour,
it is possible to use your own custom field class when decorating a `strawberry.django.type` with the `field_cls` argument, e.g.

```{.python title=types.py}
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
