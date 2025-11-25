---
title: Queries
---

# Queries

Queries are the primary way to fetch data from your GraphQL API. Strawberry Django provides powerful tools to define queries that automatically map to Django models and querysets.

## Basic Queries

Queries can be written using `strawberry_django.field()` to load the fields defined in your types.

```python title="schema.py"
import strawberry
import strawberry_django

from .types import Fruit

@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field()
    fruits: list[Fruit] = strawberry_django.field()

schema = strawberry.Schema(query=Query)
```

> [!TIP]
> You must name your query class "Query" or decorate it with `@strawberry.type(name="Query")` for the single query default primary filter to work

For single queries (like `fruit` above), Strawberry Django automatically provides a primary key filter. The `fruits` query returns all objects by default.

```graphql
query {
  # Single object by primary key
  fruit(pk: "1") {
    id
    name
  }

  # All objects
  fruits {
    id
    name
  }
}
```

## Queries with Filters

Add filters to your queries to enable flexible data filtering. Filters are defined in your types and automatically applied to queries.

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.filter_type(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
    color: auto

@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    id: auto
    name: auto
    color: auto
```

```python title="schema.py"
@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()
```

This enables powerful filtering in your GraphQL queries:

```graphql
query {
  # Exact match
  fruits(filters: { name: "apple" }) {
    id
    name
  }

  # With lookups
  fruits(filters: { name: { iContains: "berry" } }) {
    id
    name
  }

  # Complex filters with AND/OR
  fruits(
    filters: {
      OR: [{ name: { startsWith: "straw" } }, { color: { exact: "red" } }]
    }
  ) {
    id
    name
  }
}
```

See the [Filtering Guide](./filters.md) for comprehensive filter documentation.

## Queries with Ordering

Add ordering to control the sort order of your results.

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.order_type(models.Fruit)
class FruitOrder:
    name: auto
    price: auto

@strawberry_django.type(models.Fruit, order=FruitOrder)
class Fruit:
    id: auto
    name: auto
    price: auto
```

```graphql
query {
  # Order by name ascending
  fruits(order: { name: ASC }) {
    name
    price
  }

  # Order by multiple fields
  fruits(order: { price: DESC, name: ASC }) {
    name
    price
  }
}
```

See the [Ordering Guide](./ordering.md) for detailed ordering documentation.

## Queries with Pagination

Always paginate large result sets to prevent performance issues.

### Offset Pagination

```python title="schema.py"
from strawberry_django.pagination import OffsetPaginationInput

@strawberry.type
class Query:
    @strawberry_django.field
    def fruits(
        self,
        pagination: OffsetPaginationInput | None = None,
    ) -> list[Fruit]:
        qs = models.Fruit.objects.all()
        if pagination:
            return qs[pagination.offset:pagination.offset + pagination.limit]
        return qs[:100]  # Default limit
```

> [!NOTE]
> Returning `list[Fruit]` means the queryset is evaluated immediately. For paginated queries with metadata (total count, page info), use `OffsetPaginated[Fruit]` with `pagination=True` instead. See the [Pagination guide](./pagination.md) for details.

```graphql
query {
  fruits(pagination: { offset: 0, limit: 10 }) {
    id
    name
  }
}
```

### Relay-Style Cursor Pagination

```python title="schema.py"
from strawberry_django.relay import ListConnection
import strawberry_django

@strawberry.type
class Query:
    fruits: ListConnection[Fruit] = strawberry_django.connection()
```

```graphql
query {
  fruits(first: 10, after: "cursor") {
    edges {
      node {
        id
        name
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

See the [Pagination Guide](./pagination.md) for more pagination strategies.

## Custom Resolvers

Override default resolvers for custom query logic.

```python title="schema.py"
from strawberry.types import Info

@strawberry.type
class Query:
    @strawberry_django.field
    def fruits(
        self,
        info: Info,
        available_only: bool = True,
    ) -> list[Fruit]:
        qs = models.Fruit.objects.all()

        if available_only:
            qs = qs.filter(available=True)

        # Apply filters from info context
        return qs

    @strawberry_django.field
    def featured_fruits(self, info: Info) -> list[Fruit]:
        """Return only featured fruits"""
        return models.Fruit.objects.filter(
            is_featured=True,
            available=True
        ).order_by('-created_at')[:5]
```

```graphql
query {
  # All available fruits
  fruits(availableOnly: true) {
    name
  }

  # Featured fruits only
  featuredFruits {
    name
  }
}
```

See the [Custom Resolvers Guide](./resolvers.md) for advanced resolver patterns.

## Async Queries

For ASGI applications, you can define async queries for improved concurrency.

```python title="schema.py"
from asgiref.sync import sync_to_async

@strawberry.type
class Query:
    @strawberry_django.field
    async def fruits(self) -> list[Fruit]:
        # Django ORM calls must be wrapped in sync_to_async
        return await sync_to_async(list)(
            models.Fruit.objects.all()
        )

    @strawberry_django.field
    async def fruit(self, pk: int) -> Fruit | None:
        try:
            return await sync_to_async(models.Fruit.objects.get)(pk=pk)
        except models.Fruit.DoesNotExist:
            return None
```

> [!WARNING]
> Always wrap Django ORM operations in `sync_to_async` when using async resolvers. The ORM is not async-native.

## Nested Queries and Relationships

Strawberry Django automatically handles related objects with optimal queries using the Query Optimizer.

```python title="models.py"
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
```

```python title="types.py"
@strawberry_django.type(models.Author)
class Author:
    id: auto
    name: auto
    books: list['Book']

@strawberry_django.type(models.Book)
class Book:
    id: auto
    title: auto
    author: Author
```

```graphql
query {
  books {
    title
    author {
      name
      books {
        title
      }
    }
  }
}
```

The Query Optimizer automatically adds `select_related()` and `prefetch_related()` to prevent N+1 queries.

See the [Query Optimizer Guide](./optimizer.md) for optimization details.

## Query Arguments

Add custom arguments to your queries for flexibility.

```python title="schema.py"
from datetime import date

@strawberry.type
class Query:
    @strawberry_django.field
    def books(
        self,
        author_id: int | None = None,
        published_after: date | None = None,
        min_rating: float | None = None,
    ) -> list[Book]:
        qs = models.Book.objects.all()

        if author_id:
            qs = qs.filter(author_id=author_id)

        if published_after:
            qs = qs.filter(publication_date__gte=published_after)

        if min_rating:
            qs = qs.filter(rating__gte=min_rating)

        return qs
```

```graphql
query {
  books(authorId: 1, publishedAfter: "2020-01-01", minRating: 4.0) {
    title
    rating
  }
}
```

## Aggregations and Computed Fields

Use annotations for database-level aggregations.

```python title="types.py"
from django.db.models import Count, Avg
import strawberry_django

@strawberry_django.type(models.Author)
class Author:
    id: auto
    name: auto

    book_count: int = strawberry_django.field(
        annotate={'book_count': Count('books')}
    )

    avg_book_rating: float = strawberry_django.field(
        annotate={'avg_book_rating': Avg('books__rating')}
    )
```

```graphql
query {
  authors {
    name
    bookCount
    avgBookRating
  }
}
```

## Best Practices

1. **Always enable the Query Optimizer** - Add `DjangoOptimizerExtension()` to your schema
2. **Paginate list queries** - Prevent loading thousands of records
3. **Use filters and ordering** - Let clients control what data they need
4. **Add appropriate indexes** - Index fields used in filters and ordering
5. **Use custom resolvers sparingly** - Default resolvers are optimized
6. **Leverage annotations** - Perform calculations in the database
7. **Test query performance** - Monitor SQL queries during development

## Complete Example

```python title="schema.py"
import strawberry
import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginationInput

from . import models
from .types import Fruit, FruitFilter, FruitOrder

@strawberry.type
class Query:
    # Single object query with PK filter
    fruit: Fruit = strawberry_django.field()

    # List query with filters, ordering, and pagination
    @strawberry_django.field
    def fruits(
        self,
        filters: FruitFilter | None = strawberry.UNSET,
        order: FruitOrder | None = strawberry.UNSET,
        pagination: OffsetPaginationInput | None = None,
    ) -> list[Fruit]:
        qs = models.Fruit.objects.all()

        # Filters and ordering are applied automatically
        # when using strawberry_django.field

        # Apply pagination
        if pagination:
            qs = qs[pagination.offset:pagination.offset + pagination.limit]
        else:
            qs = qs[:100]  # Default limit

        return qs

    # Custom query with business logic
    @strawberry_django.field
    def featured_fruits(self) -> list[Fruit]:
        return models.Fruit.objects.filter(
            is_featured=True,
            available=True
        ).order_by('-created_at')[:10]

# Enable Query Optimizer
schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension(),
    ]
)
```

```graphql
query {
  # Get single fruit
  fruit(pk: "1") {
    id
    name
    price
  }

  # List with filters and ordering
  fruits(
    filters: { name: { iContains: "berry" } }
    order: { price: DESC }
    pagination: { offset: 0, limit: 10 }
  ) {
    id
    name
    price
  }

  # Custom query
  featuredFruits {
    id
    name
  }
}
```

## See Also

- [Filtering](./filters.md) - Comprehensive filtering guide
- [Ordering](./ordering.md) - Sort and order results
- [Pagination](./pagination.md) - Paginate large result sets
- [Query Optimizer](./optimizer.md) - Prevent N+1 queries
- [Custom Resolvers](./resolvers.md) - Advanced resolver patterns
- [Relay](./relay.md) - Relay-style connections and nodes
