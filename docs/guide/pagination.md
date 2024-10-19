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

type Query {
  fruits(pagination: PaginationInput): [Fruit!]!
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

> [!NOTE]
> There is no default limit defined. All elements are returned if no pagination limit is defined.

## Paginated Generic

For more complex pagination needs, you can use the `Paginated` generic, which alongside
the `pagination` argument, will wrap the results in an object that contains the results
and the pagination information, together with the `totalCount` of elements excluding pagination.

```python title="types.py"
from strawberry_django.pagination import Paginated


@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto


@strawberry.type
class Query:
    fruits: Paginated[Fruit] = strawberry_django.field()
```

Would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
}

type PaginatedInfo {
  limit: Int!
  offset: Int!
}

type FruitPaginated {
  pageInfo: PaginatedInfo!
  totalCount: Int!
  results: [Fruit]!
}

type Query {
  fruits(pagination: PaginationInput): [FruitPaginated!]!
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

### Customizing the pagination

Like other generics, `Paginated` can be customized to modify its behavior or to
add extra functionality in it. For example, suppose we want to add the average
price of the fruits in the pagination:

```python title="types.py"
from strawberry_django.pagination import Paginated


@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto
    price: auto


@strawberry.type
class FruitPaginated(Paginated[Fruit]):
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
    fruits: FruitPaginated = strawberry_django.field()
```

Would produce the following schema:

```graphql title="schema.graphql"
type Fruit {
  name: String!
}

type PaginatedInfo {
  limit: Int!
  offset: Int!
}

type FruitPaginated {
  pageInfo: PaginatedInfo!
  totalCount: Int!
  results: [Fruit]!
  averagePrice: Decimal!
  paginatedAveragePrice: Decimal!
}

type Query {
  fruits(pagination: PaginationInput): [FruitPaginated!]!
}
```

The following attributes/methods can be accessed in the `Paginated` class:

- `queryset`: The queryset original queryset with any filters/ordering applied,
  but not paginated yet
- `pagination`: The `OffsetPaginationInput` object, with the `offset` and `limit` for pagination
- `get_total_count()`: Returns the total count of elements in the queryset without pagination
- `get_paginated_queryset()`: Returns the queryset with pagination applied

## Cursor pagination (aka Relay style pagination)

Another option for pagination is to use a
[relay style cursor pagination](https://graphql.org/learn/pagination). For this,
you can leverage the [relay integration](./relay.md) provided by strawberry
to create a relay connection.
