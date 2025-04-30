---
title: Ordering
---

# Ordering

`@strawberry_django.ordering_type` is an upgrade from the previous `@strawberry_django.order` implementation
and allows sorting by multiple fields.

```python title="types.py"
@strawberry_django.order_type(models.Color)
class ColorOrder:
  name: auto


@strawberry_django.order_type(models.Fruit)
class FruitOrder:
  name: auto
  color: ColorOrder | None
```

> [!TIP]
> In most cases ordering fields should have `Optional` annotations and default value `strawberry.UNSET`.
> Above `auto` annotation is wrapped in `Optional` automatically.
> `UNSET` is automatically used for fields without `field` or with `strawberry_django.order_field`.

The code above generates the following schema:

```graphql title="schema.graphql"
enum Ordering {
  ASC
  ASC_NULLS_FIRST
  ASC_NULLS_LAST
  DESC
  DESC_NULLS_FIRST
  DESC_NULLS_LAST
}

input ColorOrder @oneOf {
  name: Ordering
}

input FruitOrder @oneOf {
  name: Ordering
  color: ColorOrder
}
```

As you can see, every input is automatically annotated with `@oneOf`. To express ordering by multiple fields, a
list is passed.

## Custom order methods

You can define custom order method by defining your own resolver.

```python title="types.py"
@strawberry_django.order_type(models.Fruit)
class FruitOrder:
  name: auto

  @strawberry_django.order_field
  def discovered_by(self, value: bool, prefix: str) -> list[str]:
    if not value:
      return []
    return [f"{prefix}discover_by__name", f"{prefix}name"]

  @strawberry_django.order_field
  def order_number(
          self,
          info: Info,
          queryset: QuerySet,
          value: strawberry_django.Ordering,  # `auto` can be used instead
          prefix: str,
  ) -> tuple[QuerySet, list[str]] | list[str]:
    queryset = queryset.alias(
      _ordered_num=Count(f"{prefix}orders__id")
    )
    ordering = value.resolve(f"{prefix}_ordered_num")
    return queryset, [ordering]
```

> [!WARNING]
> Do not use `queryset.order_by()` directly. Due to `order_by` not being chainable
> operation, changes applied this way would be overridden later.

> [!TIP]
> The `strawberry_django.Ordering` type has convenient method `resolve` that can be used to
> convert field's name to appropriate `F` object with correctly applied `asc()`, `desc()` method
> with `nulls_first` and `nulls_last` arguments.

The code above generates the following schema:

```graphql title="schema.graphql"
enum Ordering {
  ASC
  ASC_NULLS_FIRST
  ASC_NULLS_LAST
  DESC
  DESC_NULLS_FIRST
  DESC_NULLS_LAST
}

input FruitOrder @oneOf {
  name: Ordering
  discoveredBy: bool
  orderNumber: Ordering
}
```

#### Resolver arguments

- `prefix` - represents the current path or position
  - **Required**
  - Important for nested ordering
  - In code below custom order `name` ends up ordering `Fruit` instead of `Color` without applying `prefix`

```python title="Why prefix?"
@strawberry_django.order_type(models.Fruit)
class FruitOrder:
  name: auto
  color: ColorOrder | None


@strawberry_django.order_type(models.Color)
class ColorOrder:
  @strawberry_django.order_field
  def name(self, value: bool, prefix: str):
    # prefix is "fruit_set__" if unused root object is ordered instead
    if value:
      return ["name"]
    return []
```

```graphql
{
  fruits( ordering: [{color: name: ASC}] ) { ... }
}
```

- `value` - represents graphql field type
  - **Required**, but forbidden for default `order` method
  - _must_ be annotated
  - used instead of field's return type
  - Using `auto` is the same as `strawberry_django.Ordering`.
- `queryset` - can be used for more complex ordering
  - Optional, but **Required** for default `order` method
  - usually used to `annotate` `QuerySet`

#### Resolver return

For custom field methods two return values are supported

- iterable of values acceptable by `QuerySet.order_by` -> `Collection[F | str]`
- tuple with `QuerySet` and iterable of values acceptable by `QuerySet.order_by` -> `tuple[QuerySet, Collection[F | str]]`

For default `order` method only second variant is supported.

### What about nulls?

By default `null` values are ignored. This can be toggled as such `@strawberry_django.order_field(order_none=True)`

## Overriding the default `order` method

Works similar to field order method, but:

- is responsible for resolution of ordering for entire object
- _must_ be named `order`
- argument `queryset` is **Required**
- argument `value` is **Forbidden**

```python title="types.py"
@strawberry_django.order_type(models.Fruit)
class FruitOrder:
  name: auto

  @strawberry_django.order_field
  def ordered(
          self,
          info: Info,
          queryset: QuerySet,
          value: strawberry_django.Ordering,
          prefix: str
  ) -> tuple[QuerySet, list[str]] | list[str]:
    queryset = queryset.alias(
      _ordered_num=Count(f"{prefix}orders__id")
    )
    return queryset, [value.resolve(f"{prefix}_ordered_num")]

  @strawberry_django.order_field
  def order(
          self,
          info: Info,
          queryset: QuerySet,
          prefix: str,
  ) -> tuple[QuerySet, list[str]]:
    queryset = queryset.filter(
      ...  # Do some query modification
    )

    return strawberry_django.ordering.process_ordering_default(
      self,
      info=info,
      queryset=queryset,
      prefix=prefix,
    )

```

> [!TIP]
> As seen above `strawberry_django.ordering.process_ordering_default` function is exposed and can be
> reused in custom methods. This provides the default ordering implementation.

## Adding orderings to types

All fields and mutations inherit orderings from the underlying type by default.
So, if you have a field like this:

```python title="types.py"
@strawberry_django.type(models.Fruit, ordering=FruitOrder)
class Fruit:
    ...
```

The `fruits` field will inherit the `ordering` of the type the same way as
if it was passed to the field.

## Adding orderings directly into a field

Orderings added into a field override the default order of this type.

```python title="schema.py"
@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field(ordering=FruitOrder)
```

## Legacy Order

The previous implementation (`@strawberry_django.order`) is still available, but deprecated and only provided to allow
backwards-compatible schemas. It can be used together with `@strawberry_django.ordering.ordering`, however clients
may only specify one or the other.
You can still read the [documentation for it](legacy-ordering).
