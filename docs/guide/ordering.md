# Ordering

!!! note

    This API may change in the future.

```{.python title=types.py}
@strawberry.django.order(models.Color)
class ColorOrder:
    name: auto

@strawberry.django.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder
```

The code above generates the following schema:

```{.graphql title=schema.graphql}
enum Ordering {
  ASC
  DESC
}

input ColorOrder {
  name: Ordering
}

input FruitOrder {
  name: Ordering
  color: ColorOrder
}
```

## Adding orderings to types

All fields and mutations inherit orderings from the underlying type by default.
So, if you have a field like this:

```{.python title=types.py}
@strawberry.django.type(models.Fruit, order=FruitOrder)
class Fruit:
    ...
```

The `fruits` field will inherit the `filters` of the type same same way as
if it was passed to the field.

## Adding orderings directly into a field

Orderings added into a field override the default filters of this type.

```{.python title=schema.py}
@strawberry.type
class Query:
    fruit: Fruit = strawberry.django.field(order=FruitOrder)
```
