---
title: Pagination
---

# Pagination

## Default pagination

An interface for limit/offset pagination can be use for basic pagination needs:

```python title="types.py"
@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto


@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()
```

Would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
}

input OffsetPaginationInput {
  offset: Int! = 0
  limit: Int = null
}

type Query {
  fruits(pagination: OffsetPaginationInput): [Fruit!]!
}
```

And can be queried like:

```graphql title="schema.graphql"
query {
  fruits(pagination: { offset: 0, limit: 2 }) {
    name
  }
}
```

The `pagination` argument can be given to the type, which will enforce the pagination
argument every time the field is annotated as a list, but you can also give it directly
to the field for more control, like:

```python title="types.py"
@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto


@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field(pagination=True)
```

Which will produce the exact same schema.

### Default limit for pagination

The default limit for pagination is set to `100`. This can be changed in the
[strawberry django settings](./settings.md) to increase or decrease that number,
or even set to `None` to set it to unlimited.

### Maximum limit for pagination

To prevent clients from requesting too many records at once (which could cause performance
issues), you can configure a maximum limit using the `PAGINATION_MAX_LIMIT` setting.
When set, this will cap any limit value requested by clients, including `None` (unlimited) requests.

For example, if you set `PAGINATION_MAX_LIMIT` to `1000`, a client requesting `limit: 5000`
or `limit: null` will only receive a maximum of 1000 records.

```python title="settings.py"
STRAWBERRY_DJANGO = {
    "PAGINATION_DEFAULT_LIMIT": 100,
    "PAGINATION_MAX_LIMIT": 1000,  # Cap all pagination requests at 1000 records
}
```

By default, `PAGINATION_MAX_LIMIT` is set to `None`, which means unlimited requests are allowed.
This maintains backward compatibility but is not recommended for production environments.

### Custom pagination limits per field

To configure it on a per field basis, you can define your own `OffsetPaginationInput`
subclass and modify its default value, like:

```python
@strawberry.input
class MyOffsetPaginationInput(OffsetPaginationInput):
    limit: int = 250


# Pass it to the pagination argument when defining the type
@strawberry_django.type(models.Fruit, pagination=MyOffsetPaginationInput)
class Fruit:
    ...


@strawberry.type
class Query:
    # Or pass it to the pagination argument when defining the field
    fruits: list[Fruit] = strawberry_django.field(pagination=MyOffsetPaginationInput)
```

## OffsetPaginated Generic

For more complex pagination needs, you can use the `OffsetPaginated` generic, which alongside
the `pagination` argument, will wrap the results in an object that contains the results
and the pagination information, together with the `totalCount` of elements excluding pagination.

```python title="types.py"
from strawberry_django.pagination import OffsetPaginated


@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto


@strawberry.type
class Query:
    fruits: OffsetPaginated[Fruit] = strawberry_django.offset_paginated()
```

Would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
}

type PaginationInfo {
  limit: Int = null
  offset: Int!
}

type FruitOffsetPaginated {
  pageInfo: PaginationInfo!
  totalCount: Int!
  results: [Fruit]!
}

input OffsetPaginationInput {
  offset: Int! = 0
  limit: Int = null
}

type Query {
  fruits(pagination: OffsetPaginationInput): [FruitOffsetPaginated!]!
}
```

Which can be queried like:

```graphql title="schema.graphql"
query {
  fruits(pagination: { offset: 0, limit: 2 }) {
    totalCount
    pageInfo {
      limit
      offset
    }
    results {
      name
    }
  }
}
```

> [!NOTE]
> OffsetPaginated follow the same rules for the default pagination limit, and can be configured
> in the same way as explained above.

### Customizing queryset resolver

It is possible to define a custom resolver for the queryset to either provide a custom
queryset for it, or even to receive extra arguments alongside the pagination arguments.

Suppose we want to pre-filter a queryset of fruits for only available ones,
while also adding [ordering](./ordering.md) to it. This can be achieved with:

```python title="types.py"

@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto
    price: auto


@strawberry_django.order_type(models.Fruit)
class FruitOrder:
    name: auto
    price: auto


@strawberry.type
class Query:
    @strawberry_django.offset_paginated(OffsetPaginated[Fruit], order=FruitOrder)
    def fruits(self, only_available: bool = True) -> QuerySet[Fruit]:
        queryset = models.Fruit.objects.all()
        if only_available:
            queryset = queryset.filter(available=True)

        return queryset
```

This would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
  price: Decimal!
}

type FruitOrder {
  name: Ordering
  price: Ordering
}

type PaginationInfo {
  limit: Int!
  offset: Int!
}

type FruitOffsetPaginated {
  pageInfo: PaginationInfo!
  totalCount: Int!
  results: [Fruit]!
}

input OffsetPaginationInput {
  offset: Int! = 0
  limit: Int = null
}

type Query {
  fruits(
    onlyAvailable: Boolean! = true
    pagination: OffsetPaginationInput
    order: FruitOrder
  ): [FruitOffsetPaginated!]!
}
```

### Customizing the pagination

Like other generics, `OffsetPaginated` can be customized to modify its behavior or to
add extra functionality in it. For example, suppose we want to add the average
price of the fruits in the pagination:

```python title="types.py"
from decimal import Decimal
from strawberry_django.pagination import OffsetPaginated
from django.db.models import Avg


@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto
    price: auto


@strawberry.type
class FruitOffsetPaginated(OffsetPaginated[Fruit]):
    @strawberry_django.field
    def average_price(self) -> Decimal:
        if self.queryset is None:
            return Decimal(0)

        return self.queryset.aggregate(Avg("price"))["price__avg"]

    @strawberry_django.field
    def paginated_average_price(self) -> Decimal:
        paginated_queryset = self.get_paginated_queryset()
        if paginated_queryset is None:
            return Decimal(0)

        return paginated_queryset.aggregate(Avg("price"))["price__avg"]


@strawberry.type
class Query:
    fruits: FruitOffsetPaginated = strawberry_django.offset_paginated()
```

Would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
}

type PaginationInfo {
  limit: Int = null
  offset: Int!
}

type FruitOffsetPaginated {
  pageInfo: PaginationInfo!
  totalCount: Int!
  results: [Fruit]!
  averagePrice: Decimal!
  paginatedAveragePrice: Decimal!
}

input OffsetPaginationInput {
  offset: Int! = 0
  limit: Int = null
}

type Query {
  fruits(pagination: OffsetPaginationInput): [FruitOffsetPaginated!]!
}
```

The following attributes/methods can be accessed in the `OffsetPaginated` class:

- `queryset`: The queryset original queryset with any filters/ordering applied,
  but not paginated yet
- `pagination`: The `OffsetPaginationInput` object, with the `offset` and `limit` for pagination
- `get_total_count()`: Returns the total count of elements in the queryset without pagination
- `get_paginated_queryset()`: Returns the queryset with pagination applied
- `resolve_paginated(queryset, *, info, pagination, **kwargs)`: The classmethod that
  strawberry-django calls to create an instance of the `OffsetPaginated` class/subclass.

## Cursor pagination (aka Relay style pagination)

Another option for pagination is to use a
[relay style cursor pagination](https://graphql.org/learn/pagination). For this,
you can leverage the [relay integration](./relay.md) provided by strawberry
to create a relay connection.
