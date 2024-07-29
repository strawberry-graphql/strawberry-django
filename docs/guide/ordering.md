---
title: Ordering
---

# Ordering

```python title="types.py"
@strawberry_django.order(models.Color)
class ColorOrder:
    name: auto

@strawberry_django.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder | None
```

> [!TIP]
> In most cases order fields should have `Optional` annotations and default value `strawberry.UNSET`.
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

input ColorOrder {
  name: Ordering
}

input FruitOrder {
  name: Ordering
  color: ColorOrder
}
```

## Custom order methods

You can define custom order method by defining your own resolver.

```python title="types.py"
@strawberry_django.order(models.Fruit)
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
        value: strawberry_django.Ordering, # `auto` can be used instead
        prefix: str,
        sequence: dict[str, strawberry_django.Ordering] | None
    ) -> tuple[QuerySet, list[str]] | list[str]:
        queryset = queryset.alias(
            _ordered_num=Count(f"{prefix}orders__id")
        )
        ordering = value.resolve(f"{prefix}_ordered_num")
        return queryset, [ordering]
```

> [!WARNING]
> Do not use `queryset.order_by()` directly. Due to `order_by` not being chainable
> operation, changes applied this way would be overriden later.

> [!TIP] > `strawberry_django.Ordering` has convenient method `resolve` that can be used to
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

input FruitOrder {
  name: Ordering
  discoveredBy: bool
  orderNumber: Ordering
}
```

#### Resolver arguments

- `prefix` - represents the current path or position
  - **Required**
  - Important for nested ordering
  - In code bellow custom order `name` ends up ordering `Fruit` instead of `Color` without applying `prefix`

```python title="Why prefix?"
@strawberry_django.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder | None

@strawberry_django.order(models.Color)
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
  fruits( order: {color: name: ASC} ) { ... }
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
- `sequence` - used to order values on the same level
  - elements in graphql object are not quaranteed to keep their order as defined by user thus
    this argument should be used in those cases
    [GraphQL Spec](https://spec.graphql.org/October2021/#sec-Language.Arguments)
  - usually for custom order field methods does not have to be used
  - for advanced usage, look at `strawberry_django.process_order` function

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
- should probaly use `sequence`

```python title="types.py"
@strawberry_django.order(models.Fruit)
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
        return queryset, [value.resolve(f"{prefix}_ordered_num") ]

    @strawberry_django.order_field
    def order(
        self,
        info: Info,
        queryset: QuerySet,
        prefix: str,
        sequence: dict[str, strawberry_django.Ordering] | None
    ) -> tuple[QuerySet, list[str]]:
        queryset = queryset.filter(
            ... # Do some query modification
        )

        return strawberry_django.process_order(
            self,
            info=info,
            queryset=queryset,
            sequence=sequence,
            prefix=prefix,
            skip_object_order_method=True
        )

```

> [!TIP]
> As seen above `strawberry_django.process_order` function is exposed and can be
> reused in custom methods.
> For order method `order` `skip_object_order_method` was used to avoid endless recursion.

## Adding orderings to types

All fields and mutations inherit orderings from the underlying type by default.
So, if you have a field like this:

```python title="types.py"
@strawberry_django.type(models.Fruit, order=FruitOrder)
class Fruit:
    ...
```

The `fruits` field will inherit the `order` of the type same same way as
if it was passed to the field.

## Adding orderings directly into a field

Orderings added into a field override the default order of this type.

```python title="schema.py"
@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field(order=FruitOrder)
```
