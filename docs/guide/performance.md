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

Beyond query optimization, optimize your database schema and queries.

### Indexes

Add indexes for frequently queried fields:

```python
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    isbn = models.CharField(max_length=13, unique=True)  # Unique adds index
    publication_date = models.DateField(db_index=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)  # FK auto-indexed

    class Meta:
        indexes = [
            # Composite indexes for common queries
            models.Index(fields=['author', 'publication_date']),
            models.Index(fields=['title', 'author']),

            # Partial index (PostgreSQL)
            models.Index(
                fields=['publication_date'],
                name='recent_books_idx',
                condition=models.Q(publication_date__gte='2020-01-01')
            ),
        ]
```

### Database Functions and Aggregations

Use database functions for calculations:

```python
from django.db.models import F, Q, Count, Sum, Avg
from django.db.models.functions import Lower, Concat

@strawberry.type
class Query:
    @strawberry.field
    def books(
        self,
        min_rating: Optional[float] = None
    ) -> List[BookType]:
        qs = Book.objects.all()

        # Filter using database
        if min_rating:
            qs = qs.filter(rating__gte=min_rating)

        # Annotate aggregations
        qs = qs.annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating'),
            full_title=Concat('title', models.Value(' - '), 'subtitle')
        )

        return qs
```

### Efficient Counting

```python
# Bad: Loads all objects into memory
books = Book.objects.all()
count = len(books)  # Fetches all records!

# Good: Count in database
count = Book.objects.count()

# Even better: exists() for boolean checks
has_books = Book.objects.exists()
```

### Efficient Existence Checks

```python
# Bad: Fetches objects
if Book.objects.filter(author=author):
    # ...

# Good: Just check existence
if Book.objects.filter(author=author).exists():
    # ...

# For counting small numbers, filter + limit
recent_books = Book.objects.filter(
    publication_date__gte=date.today() - timedelta(days=30)
)[:5]  # Limit early

if len(recent_books) >= 5:
    # Handle case with many recent books
```

### Bulk Operations

```python
# Bad: Multiple queries
for book in books:
    book.is_featured = True
    book.save()  # One query per book!

# Good: Bulk update
Book.objects.filter(id__in=book_ids).update(is_featured=True)

# Bulk create
books_to_create = [
    Book(title=f"Book {i}", author=author)
    for i in range(100)
]
Book.objects.bulk_create(books_to_create)  # Single query

# Bulk update with different values (Django 4.2+)
Book.objects.bulk_update(books, ['title', 'rating'])
```

### Select Only Needed Fields

```python
# Bad: Fetches all fields
books = Book.objects.all()

# Good: Fetch only what you need
books = Book.objects.only('id', 'title', 'author_id')

# Or exclude large fields
books = Book.objects.defer('description', 'content')
```

### Raw Queries for Complex Operations

```python
from django.db import connection

@strawberry.field
def complex_statistics(self) -> StatisticsType:
    """Use raw SQL for complex queries optimizer can't handle"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                author_id,
                COUNT(*) as book_count,
                AVG(rating) as avg_rating,
                SUM(sales) as total_sales
            FROM books
            WHERE publication_date >= %s
            GROUP BY author_id
            HAVING COUNT(*) > %s
        """, [start_date, min_books])

        results = cursor.fetchall()

    return process_results(results)
```

## Caching Strategies

Implement caching at multiple levels for maximum performance.

### Django Cache Framework

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache query results
@strawberry.field
def featured_books(self) -> List[BookType]:
    cache_key = 'featured_books'

    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Fetch from database
    books = Book.objects.filter(is_featured=True)[:10]

    # Cache for 1 hour
    cache.set(cache_key, books, 3600)

    return books
```

### Field-Level Caching

```python
from django.core.cache import cache
import strawberry_django

@strawberry_django.type(Author)
class AuthorType:
    name: strawberry.auto

    @strawberry.field
    def book_count(self) -> int:
        """Cache computed values"""
        cache_key = f'author_book_count_{self.id}'
        count = cache.get(cache_key)
        if count is None:
            count = self.books.count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        return count
```

> [!WARNING]
> Don't use `@lru_cache` on instance methods as it can lead to memory leaks. Use Django's cache framework or `cached_property` instead.

### Cache Invalidation

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=Book)
def invalidate_book_cache(sender, instance, **kwargs):
    """Invalidate cache when books change"""
    cache.delete('featured_books')
    cache.delete(f'author_books_{instance.author_id}')
```

### Redis Caching

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'strawberry',
        'TIMEOUT': 300,
    }
}

# Use in resolvers
from django.core.cache import cache

@strawberry.field
def expensive_computation(self, id: int) -> ResultType:
    cache_key = f'computation_{id}'

    result = cache.get(cache_key)
    if result is None:
        result = perform_expensive_computation(id)
        cache.set(cache_key, result, timeout=3600)

    return result
```

### HTTP Caching with ETags

```python
from django.views.decorators.http import condition
from django.utils.http import http_date

def latest_book_date(request, *args, **kwargs):
    """Get last modification time for ETag"""
    latest = Book.objects.latest('updated_at')
    return latest.updated_at

@condition(last_modified_func=latest_book_date)
def graphql_view(request):
    # GraphQL view with HTTP caching
    pass
```

## Query Complexity

Limit query complexity to prevent expensive operations.

### Query Depth Limiting

Use Strawberry's built-in query depth limiter to prevent overly complex queries:

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

For custom complexity analysis, you can implement a custom extension. See [Strawberry Extensions](https://strawberry.rocks/docs/guides/extensions) for more details.

### Rate Limiting

```python
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

def rate_limit(key: str, limit: int, period: int):
    """Rate limit decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f'rate_limit_{key}'
            count = cache.get(cache_key, 0)

            if count >= limit:
                raise PermissionDenied("Rate limit exceeded")

            cache.set(cache_key, count + 1, period)
            return func(*args, **kwargs)

        return wrapper
    return decorator

@strawberry.type
class Query:
    @strawberry.field
    @rate_limit('search', limit=100, period=3600)  # 100 per hour
    def search_books(self, query: str) -> List[BookType]:
        return Book.objects.filter(title__icontains=query)
```

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

### Performance Tips for Pagination

```python
# Bad: Count(*) on large tables
total_count = Book.objects.count()  # Slow on millions of rows

# Good: Estimate or cache
cached_count = cache.get('book_count')
if not cached_count:
    cached_count = Book.objects.count()
    cache.set('book_count', cached_count, 3600)

# Even better: Use approximate counts (PostgreSQL)
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT reltuples::bigint AS estimate
        FROM pg_class
        WHERE relname = 'books'
    """)
    estimate = cursor.fetchone()[0]
```

## Monitoring and Profiling

Monitor performance to identify bottlenecks.

### Django Debug Toolbar

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
    'strawberry_django',
]

MIDDLEWARE = [
    # ...
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Enables query debugging in development
```

### Query Logging

```python
import logging
from django.db import connection

# Enable query logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('django.db.backends')
logger.setLevel(logging.DEBUG)

@strawberry.field
def books(self) -> List[BookType]:
    # Run query
    result = Book.objects.all()

    # Log queries
    for query in connection.queries:
        print(f"Query: {query['sql']}")
        print(f"Time: {query['time']}")

    return result
```

### Custom Performance Monitoring

```python
import time
from functools import wraps

def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        queries_before = len(connection.queries)

        result = func(*args, **kwargs)

        elapsed = time.time() - start
        queries_count = len(connection.queries) - queries_before

        print(f"{func.__name__}: {elapsed:.3f}s, {queries_count} queries")

        return result

    return wrapper

@strawberry.type
class Query:
    @strawberry.field
    @log_performance
    def books(self) -> List[BookType]:
        return Book.objects.all()
```

### APM Integration (New Relic, Datadog, etc.)

```python
# Example with New Relic
import newrelic.agent

@strawberry.type
class Query:
    @strawberry.field
    @newrelic.agent.function_trace()
    def books(self) -> List[BookType]:
        return Book.objects.all()
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

### 4. Use Bulk Operations

```python
# Bad: Loop with saves
for book in books:
    book.is_published = True
    book.save()

# Good: Bulk update
Book.objects.filter(id__in=[b.id for b in books]).update(is_published=True)
```

### 5. Cache Expensive Computations

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

### 6. Monitor Query Performance

```python
# Use Django Debug Toolbar in development
# Monitor slow queries in production
# Set up alerts for N+1 queries
```

## Common Patterns

### Pattern 1: Efficient Filtering

```python
@strawberry.type
class Query:
    @strawberry.field
    def books(
        self,
        author_id: Optional[int] = None,
        published_after: Optional[date] = None,
    ) -> List[BookType]:
        qs = Book.objects.all()

        # Build query incrementally
        if author_id:
            qs = qs.filter(author_id=author_id)

        if published_after:
            qs = qs.filter(publication_date__gte=published_after)

        # Apply optimizer hints
        qs = qs.select_related('author', 'publisher')

        return qs[:100]  # Always limit
```

### Pattern 2: Computed Fields with Annotations

```python
from django.db.models import Count, Avg

@strawberry_django.type(Author)
class AuthorType:
    name: str

    # Use annotations for aggregations
    book_count: int = strawberry_django.field(
        annotate={'book_count': Count('books')}
    )

    avg_book_rating: float = strawberry_django.field(
        annotate={'avg_book_rating': Avg('books__rating')}
    )
```

### Pattern 3: Use Model Properties with Optimization Hints

```python
from strawberry_django.descriptors import model_property
from django.db.models import Count

class Author(models.Model):
    name = models.CharField(max_length=100)

    @model_property(annotate={'_book_count': Count('books')})
    def book_count(self) -> int:
        """Cache-friendly computed property"""
        return self._book_count  # type: ignore
```

### Pattern 4: Prefetch Related Lists

```python
from django.db.models import Prefetch

@strawberry.field
def authors_with_books(self) -> List[AuthorType]:
    # Prefetch related books efficiently
    return Author.objects.prefetch_related(
        Prefetch(
            'books',
            queryset=Book.objects.filter(is_published=True).order_by('-publication_date')
        )
    )
```

## Troubleshooting

### Too Many Database Queries

**Problem**: Query count is very high for basic operations.

**Solution**: Enable query logging and identify N+1 queries:

```python
from django.db import connection, reset_queries
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_queries():
    reset_queries()

    # Run your query
    result = execute_graphql_query()

    print(f"Total queries: {len(connection.queries)}")
    for i, query in enumerate(connection.queries):
        print(f"{i}: {query['sql'][:100]}")
```

### Query Optimizer Not Working

**Problem**: Optimizer extension added but still seeing N+1.

**Check**:

1. Extension is properly registered
2. Using strawberry_django types (not plain strawberry types)
3. Fields are properly typed with relationships

```python
# Won't work - missing optimizer extension
schema = strawberry.Schema(query=Query)

# Works - optimizer registered
schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension()]
)
```

### Slow Aggregations

**Problem**: Counting or aggregating large datasets is slow.

**Solution**: Use database-level aggregations and caching:

```python
from django.db.models import Count

# Slow: Python-level counting
authors = Author.objects.all()
for author in authors:
    book_count = author.books.count()  # N queries!

# Fast: Database aggregation
authors = Author.objects.annotate(
    book_count=Count('books')
)
```

### Memory Issues with Large Querysets

**Problem**: Loading too many objects into memory.

**Solution**: Use pagination and iterator():

```python
# Bad: Loads everything into memory
all_books = Book.objects.all()  # Could be millions!

# Good: Paginate
books = Book.objects.all()[:100]

# Good: Iterator for batch processing
for book in Book.objects.iterator(chunk_size=1000):
    process_book(book)
```

## See Also

- [Query Optimizer](optimizer.md) - Detailed optimizer documentation
- [DataLoaders](dataloaders.md) - DataLoader patterns and usage
- [Pagination](pagination.md) - Pagination strategies
- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/) - Django's optimization guide
