# Performance Optimization

Performance is critical for GraphQL APIs, especially when dealing with complex queries and large datasets. This guide covers strategies to optimize your Strawberry Django application for maximum performance.

## Table of Contents

- [Overview](#overview)
- [The N+1 Query Problem](#the-n1-query-problem)
- [Query Optimizer](#query-optimizer)
- [DataLoaders](#dataloaders)
- [Database Optimization](#database-optimization)
- [Caching Strategies](#caching-strategies)
- [Query Complexity](#query-complexity)
- [Pagination](#pagination)
- [Monitoring and Profiling](#monitoring-and-profiling)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

GraphQL's flexibility can lead to performance issues if not handled properly. Key challenges:

1. **N+1 queries** - Multiple database queries for related objects
2. **Over-fetching** - Retrieving more data than needed
3. **Complex queries** - Deeply nested or expensive operations
4. **Duplicate queries** - Same data fetched multiple times

Strawberry Django provides several tools to address these:

- **Query Optimizer** - Automatic `select_related()` and `prefetch_related()`
- **DataLoaders** - Batching and caching for custom data fetching
- **Pagination** - Limit result sets to manageable sizes
- **Caching** - Store computed results

## The N+1 Query Problem

The N+1 problem occurs when fetching a list of objects (1 query) and then fetching related objects for each item (N queries).

### Example Problem

```python
# models.py
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

# schema.py
import strawberry
import strawberry_django

@strawberry_django.type(Author)
class AuthorType:
    name: strawberry.auto

@strawberry_django.type(Book)
class BookType:
    title: strawberry.auto
    author: AuthorType  # N+1 problem here!

@strawberry.type
class Query:
    @strawberry.field
    def books(self) -> list[BookType]:
        return Book.objects.all()
```

```graphql
query {
  books {
    # 1 query
    title
    author {
      # N queries (one per book!)
      name
    }
  }
}
```

**Without optimization**: 1 + N queries (if 100 books = 101 queries!)

### Solution: Query Optimizer Extension

```python
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension(),  # Automatically optimizes queries
    ]
)
```

**With optimizer**: 2 queries (1 for books + 1 JOIN for authors)

The optimizer automatically:

- Uses `select_related()` for foreign keys and one-to-one relationships
- Uses `prefetch_related()` for many-to-many and reverse foreign keys
- Adds `only()` to fetch only requested fields (turned off for mutations)
- Handles nested relationships

## Query Optimizer

The query optimizer analyzes your GraphQL query and optimizes the database queries.

### Basic Usage

```python
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension(),
    ]
)
```

### How It Works

```python
# models.py
class Publisher(models.Model):
    name = models.CharField(max_length=100)

class Author(models.Model):
    name = models.CharField(max_length=100)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    isbn = models.CharField(max_length=13)
```

```graphql
query {
  books {
    title
    isbn
    author {
      name
      publisher {
        name
      }
    }
  }
}
```

**Without optimizer**:

```python
# Query 1: Get all books
Book.objects.all()

# Query 2-N: Get author for each book
Author.objects.get(id=book.author_id)

# Query N+1-2N: Get publisher for each author
Publisher.objects.get(id=author.publisher_id)
```

**With optimizer**:

```python
# Single optimized query
Book.objects.all() \
    .select_related('author__publisher') \
    .only('title', 'isbn', 'author__name', 'author__publisher__name')
```

### Manual Optimization Hints

You can provide hints to the optimizer using field options:

```python
import strawberry
from strawberry_django import field

@strawberry_django.type(Book)
class BookType:
    title: str
    author: AuthorType = field(
        # Optimization hints
        select_related=['author__publisher'],
        prefetch_related=['author__books'],
        only=['author__name'],
    )
```

### Disabling Optimizer for Specific Fields

```python
from strawberry_django import field

@strawberry_django.type(Book)
class BookType:
    title: str

    # Disable optimizer for custom logic
    @field(disable_optimization=True)
    def computed_field(self) -> str:
        # Custom logic that doesn't benefit from optimization
        return self.do_custom_calculation()
```

### Annotate for Aggregations

```python
from django.db.models import Count, Avg
from strawberry_django import field

@strawberry_django.type(Author)
class AuthorType:
    name: str

    # Annotate with aggregation
    book_count: int = field(
        annotate={'book_count': Count('books')}
    )

    avg_rating: float = field(
        annotate={'avg_rating': Avg('books__rating')}
    )
```

## DataLoaders

For complex scenarios where the optimizer isn't enough, use DataLoaders.

### When to Use DataLoaders

Use DataLoaders when:

- Fetching data from external APIs
- Complex computed values requiring multiple queries
- Custom aggregations or calculations
- Non-standard relationship patterns

See the [DataLoaders Guide](dataloaders.md) for comprehensive documentation.

### Basic DataLoader Pattern

```python
from strawberry.dataloader import DataLoader
from typing import List

async def load_authors(keys: List[int]) -> List[Author]:
    """Batch load authors by ID"""
    authors = Author.objects.filter(id__in=keys)
    author_map = {author.id: author for author in authors}
    return [author_map.get(key) for key in keys]

# In context
def get_context():
    return {
        'author_loader': DataLoader(load_fn=load_authors)
    }

# In resolver
@strawberry.field
async def author(self, info) -> Author:
    loader = info.context['author_loader']
    return await loader.load(self.author_id)
```

## Database Optimization

Beyond GraphQL-specific optimizations, add database indexes for fields used in GraphQL filters and ordering:

```python
class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    publication_date = models.DateField(db_index=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['author', 'publication_date']),
        ]
```

Use database aggregations in GraphQL resolvers:

```python
from django.db.models import Count, Avg

@strawberry_django.type(models.Author)
class Author:
    name: auto
    book_count: int = strawberry_django.field(annotate={'book_count': Count('books')})
    avg_rating: float = strawberry_django.field(annotate={'avg_rating': Avg('books__rating')})
```

For general Django database optimization (bulk operations, efficient queries, etc.), see the [Django database optimization documentation](https://docs.djangoproject.com/en/stable/topics/db/optimization/).

## Caching Strategies

Cache expensive resolver computations using Django's cache framework:

```python
from django.core.cache import cache

@strawberry.field
def featured_books(self) -> List[BookType]:
    cache_key = 'featured_books'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    books = Book.objects.filter(is_featured=True)[:10]
    cache.set(cache_key, books, 3600)  # Cache for 1 hour
    return books
```

> [!WARNING]
> Don't use `@lru_cache` on instance methods as it can lead to memory leaks. Use Django's cache framework or `cached_property` instead.

For cache configuration and invalidation strategies, see [Django's cache documentation](https://docs.djangoproject.com/en/stable/topics/cache/).

## Query Complexity

Limit query complexity to prevent expensive operations using Strawberry's built-in extensions:

```python
import strawberry
from strawberry.extensions import QueryDepthLimiter

schema = strawberry.Schema(
    query=Query,
    extensions=[
        QueryDepthLimiter(max_depth=10),  # Prevent deeply nested queries
    ]
)
```

For custom complexity analysis and rate limiting, see [Strawberry Extensions](https://strawberry.rocks/docs/guides/extensions).

## Pagination

Always paginate large result sets.

### Offset Pagination

```python
from strawberry_django.pagination import OffsetPaginationInput

import strawberry_django
from strawberry_django.pagination import OffsetPaginated

@strawberry.type
class Query:
    # Use built-in pagination support
    books: OffsetPaginated[BookType] = strawberry_django.field(pagination=True)
```

> [!TIP]
> For production, use the built-in pagination support instead of manual slicing. See the [Pagination guide](./pagination.md) for details.

### Cursor Pagination (Relay)

```python
from strawberry import relay
import strawberry_django

@strawberry.type
class Query:
    books: relay.Connection[BookType] = strawberry_django.connection()

# Efficiently handles large datasets
# Better for infinite scroll
# Stable across data changes
```



## Monitoring and Profiling

Use Django Debug Toolbar in development to identify N+1 queries:

```python
# settings.py
INSTALLED_APPS = [
    'debug_toolbar',
    # ...
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]
```

Enable query logging to monitor database queries:

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Best Practices

### 1. Always Use the Query Optimizer

```python
# Always include the optimizer extension
schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension(),
    ]
)
```

### 2. Paginate All List Queries

```python
# Bad: Unbounded lists
@strawberry.field
def books(self) -> List[BookType]:
    return Book.objects.all()  # Could return millions!

# Good: Always paginate
@strawberry.field
def books(
    self,
    pagination: OffsetPaginationInput = OffsetPaginationInput(offset=0, limit=20)
) -> List[BookType]:
    return Book.objects.all()[pagination.offset:pagination.offset + pagination.limit]
```

### 3. Add Database Indexes

```python
# Index fields used in filters and ordering
class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    publication_date = models.DateField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['author', 'publication_date']),
        ]
```

### 4. Cache Expensive Computations

```python
from django.core.cache import cache

@strawberry.field
def statistics(self) -> StatisticsType:
    cached = cache.get('statistics')
    if cached:
        return cached

    stats = compute_expensive_statistics()
    cache.set('statistics', stats, 300)  # 5 minutes
    return stats
```

### 5. Monitor Query Performance

Use Django Debug Toolbar in development and enable query logging to identify performance bottlenecks.

## Common Patterns

### Computed Fields with Annotations

```python
from django.db.models import Count, Avg

@strawberry_django.type(models.Author)
class Author:
    name: auto
    book_count: int = strawberry_django.field(annotate={'book_count': Count('books')})
    avg_rating: float = strawberry_django.field(annotate={'avg_rating': Avg('books__rating')})
```

### Model Properties with Optimization Hints

```python
from strawberry_django.descriptors import model_property
from django.db.models import Count

class Author(models.Model):
    name = models.CharField(max_length=100)

    @model_property(annotate={'_book_count': Count('books')})
    def book_count(self) -> int:
        return self._book_count  # type: ignore
```

## Troubleshooting

### Too Many Database Queries

Enable query logging to identify N+1 queries. Ensure the [Query Optimizer](./optimizer.md) extension is registered and you're using `strawberry_django` types.

### Slow Aggregations

Use database-level aggregations with `annotate` instead of Python-level counting:

```python
from django.db.models import Count

# ❌ Slow: N queries
for author in Author.objects.all():
    book_count = author.books.count()

# ✅ Fast: Single query with annotation
authors = Author.objects.annotate(book_count=Count('books'))
```

### Memory Issues

Always paginate large result sets. See the [Pagination guide](./pagination.md) for details.

## See Also

- [Query Optimizer](optimizer.md) - Detailed optimizer documentation
- [DataLoaders](dataloaders.md) - DataLoader patterns and usage
- [Pagination](pagination.md) - Pagination strategies
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/) - Django's optimization guide
