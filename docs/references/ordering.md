# Ordering

> NOTE: this API may still change

```python
@strawberry.django.ordering.order(models.Color)
class ColorOrder:
    name: auto

@strawberry.django.ordering.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder
```

The code above generates the following schema:

```graphql
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

```python
@strawberry.django.type(models.Fruit, order=FruitOrder)
class Fruit:
    ...
```

## Adding orderings directly into a field

Orderings added into a field override the default filters of this type.

```python
@strawberry.type
class Query:
    fruit: Fruit = strawberry.django.field(order=FruitOrder)
```
