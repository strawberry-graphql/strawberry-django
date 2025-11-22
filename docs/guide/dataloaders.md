---
title: DataLoaders
---

# DataLoaders Integration

DataLoaders are a powerful pattern for batching and caching database queries, helping to solve the N+1 query problem in GraphQL APIs. While Strawberry Django's [Query Optimizer](./optimizer.md) handles many optimization scenarios automatically, DataLoaders provide additional control for complex cases.

## When to Use DataLoaders

Use DataLoaders when:

1. **The Query Optimizer isn't sufficient** for your use case
2. **You need custom batching logic** beyond standard Django ORM operations
3. **You're fetching data from external APIs** or non-Django data sources
4. **You need fine-grained caching control** within a single request
5. **You have complex computed fields** that require batched data fetching

> [!TIP]
> For most Django ORM queries, the [Query Optimizer Extension](./optimizer.md) is recommended as it requires less code and handles common cases automatically. Use DataLoaders for special scenarios where you need more control.

## Prerequisites

DataLoaders require ASGI to function properly. Ensure you're using `AsyncGraphQLView`:

```python title="urls.py"
from django.urls import path
from strawberry.django.views import AsyncGraphQLView

from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```

See the [Views guide](./views.md) for more information on ASGI setup.

## Basic DataLoader Usage

### Creating a Simple DataLoader

```python title="dataloaders.py"
from typing import List
from strawberry.dataloader import DataLoader
from asgiref.sync import sync_to_async

from . import models

async def load_authors(keys: List[int]) -> List[models.Author]:
    """Batch load authors by their IDs."""
    # Fetch all authors in a single query
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=keys)
    )

    # Create a mapping of id -> author
    author_map = {author.id: author for author in authors}

    # Return authors in the same order as keys
    # Return None for missing keys
    return [author_map.get(key) for key in keys]


def get_author_loader() -> DataLoader[int, models.Author]:
    """Get or create an author DataLoader."""
    return DataLoader(load_fn=load_authors)
```

### Using DataLoader in a Resolver

```python title="types.py"
import strawberry
import strawberry_django
from strawberry.types import Info

from .dataloaders import get_author_loader

@strawberry_django.type(models.Book)
class Book:
    id: strawberry.auto
    title: strawberry.auto
    author_id: strawberry.Private[int]  # Private field, not exposed in schema

    @strawberry.field
    async def author(self, info: Info) -> "Author":
        """Load author using DataLoader."""
        loader = get_author_loader()
        return await loader.load(self.author_id)
```

## DataLoader Context Pattern

Store DataLoaders in the context to reuse them across the request:

### Setting Up Context

```python title="context.py"
from typing import Any
from strawberry.types import Info
from strawberry.dataloader import DataLoader

from . import models
from .dataloaders import load_authors, load_books_by_author

class MyGraphQLContext:
    def __init__(self, request):
        self.request = request
        self._loaders = {}

    @property
    def author_loader(self) -> DataLoader[int, models.Author]:
        if 'author' not in self._loaders:
            self._loaders['author'] = DataLoader(load_fn=load_authors)
        return self._loaders['author']

    @property
    def books_by_author_loader(self) -> DataLoader[int, list[models.Book]]:
        if 'books_by_author' not in self._loaders:
            self._loaders['books_by_author'] = DataLoader(
                load_fn=load_books_by_author
            )
        return self._loaders['books_by_author']


def get_context(request) -> MyGraphQLContext:
    return MyGraphQLContext(request)
```

```python title="urls.py"
from strawberry.django.views import AsyncGraphQLView
from .schema import schema
from .context import get_context

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(
        schema=schema,
        context_getter=get_context
    )),
]
```

### Using Context DataLoaders

```python title="types.py"
@strawberry_django.type(models.Book)
class Book:
    id: strawberry.auto
    title: strawberry.auto
    author_id: strawberry.Private[int]

    @strawberry.field
    async def author(self, info: Info) -> "Author":
        context = info.context
        return await context.author_loader.load(self.author_id)


@strawberry_django.type(models.Author)
class Author:
    id: strawberry.auto
    name: strawberry.auto

    @strawberry.field
    async def books(self, info: Info) -> list[Book]:
        context = info.context
        return await context.books_by_author_loader.load(self.id)
```

## Common DataLoader Patterns

### Pattern 1: One-to-Many Relationships

Loading multiple related objects for a parent:

```python title="dataloaders.py"
from collections import defaultdict

async def load_books_by_author(author_ids: List[int]) -> List[List[models.Book]]:
    """Batch load books for multiple authors."""
    books = await sync_to_async(list)(
        models.Book.objects.filter(author_id__in=author_ids)
    )

    # Group books by author_id
    books_by_author = defaultdict(list)
    for book in books:
        books_by_author[book.author_id].append(book)

    # Return lists in the same order as author_ids
    return [books_by_author[author_id] for author_id in author_ids]
```

### Pattern 2: Many-to-Many Relationships

```python title="dataloaders.py"
async def load_tags_for_articles(article_ids: List[int]) -> List[List[models.Tag]]:
    """Batch load tags for multiple articles."""
    # Use prefetch_related for M2M efficiency
    articles = await sync_to_async(list)(
        models.Article.objects.filter(id__in=article_ids)
        .prefetch_related('tags')
    )

    # Create mapping
    tags_by_article = {
        article.id: list(article.tags.all())
        for article in articles
    }

    return [tags_by_article.get(article_id, []) for article_id in article_ids]
```

### Pattern 3: Computed/Aggregated Values

```python title="dataloaders.py"
from django.db.models import Count, Avg

async def load_book_statistics(author_ids: List[int]) -> List[dict]:
    """Batch load book statistics for authors."""
    stats = await sync_to_async(list)(
        models.Author.objects.filter(id__in=author_ids)
        .annotate(
            book_count=Count('books'),
            avg_rating=Avg('books__rating')
        )
        .values('id', 'book_count', 'avg_rating')
    )

    stats_by_author = {
        stat['id']: {
            'book_count': stat['book_count'],
            'avg_rating': stat['avg_rating'] or 0.0
        }
        for stat in stats
    }

    return [
        stats_by_author.get(author_id, {'book_count': 0, 'avg_rating': 0.0})
        for author_id in author_ids
    ]
```

Usage:

```python title="types.py"
@strawberry_django.type(models.Author)
class Author:
    id: strawberry.auto
    name: strawberry.auto

    @strawberry.field
    async def book_count(self, info: Info) -> int:
        stats = await info.context.book_stats_loader.load(self.id)
        return stats['book_count']

    @strawberry.field
    async def average_rating(self, info: Info) -> float:
        stats = await info.context.book_stats_loader.load(self.id)
        return stats['avg_rating']
```

### Pattern 4: External API Integration

DataLoaders work great for batching external API calls:

```python title="dataloaders.py"
import httpx

async def load_github_users(usernames: List[str]) -> List[dict]:
    """Batch load GitHub user data."""
    async with httpx.AsyncClient() as client:
        # In practice, you'd want to batch these into a single API call
        # if the API supports it
        tasks = [
            client.get(f"https://api.github.com/users/{username}")
            for username in usernames
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            response.json() if not isinstance(response, Exception) else None
            for response in responses
        ]
```

## Advanced Patterns

### Custom Cache Keys

Use custom cache keys for complex scenarios:

```python title="dataloaders.py"
from dataclasses import dataclass

@dataclass(frozen=True)
class BookFilterKey:
    author_id: int
    published_year: int

async def load_filtered_books(
    keys: List[BookFilterKey]
) -> List[List[models.Book]]:
    """Load books filtered by author and year."""
    # Build complex query
    books_by_key = {}

    for key in keys:
        books = await sync_to_async(list)(
            models.Book.objects.filter(
                author_id=key.author_id,
                published_date__year=key.published_year
            )
        )
        books_by_key[key] = books

    return [books_by_key.get(key, []) for key in keys]
```

Usage:

```python title="types.py"
@strawberry_django.type(models.Author)
class Author:
    id: strawberry.auto
    name: strawberry.auto

    @strawberry.field
    async def books_by_year(
        self,
        info: Info,
        year: int
    ) -> list[Book]:
        loader = info.context.filtered_books_loader
        key = BookFilterKey(author_id=self.id, published_year=year)
        return await loader.load(key)
```

### Combining with Query Optimizer

You can use DataLoaders alongside the Query Optimizer:

```python title="types.py"
@strawberry_django.type(models.Author)
class Author:
    id: strawberry.auto
    name: strawberry.auto

    # This field uses the Query Optimizer
    books: list[Book] = strawberry_django.field()

    # This field uses a DataLoader for custom logic
    @strawberry.field
    async def featured_books(self, info: Info) -> list[Book]:
        """Get featured books using custom DataLoader."""
        return await info.context.featured_books_loader.load(self.id)
```

### Prefetching with Select/Prefetch Related

Optimize DataLoader queries with Django's ORM features:

```python title="dataloaders.py"
async def load_authors_with_publishers(
    author_ids: List[int]
) -> List[models.Author]:
    """Load authors with their publishers prefetched."""
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=author_ids)
        .select_related('publisher')  # Join publisher
        .prefetch_related('books')    # Prefetch books
    )

    author_map = {author.id: author for author in authors}
    return [author_map.get(key) for key in author_ids]
```

## Error Handling

Handle errors gracefully in DataLoaders:

```python title="dataloaders.py"
import logging

logger = logging.getLogger(__name__)

async def load_authors(keys: List[int]) -> List[models.Author | None]:
    """Load authors with error handling."""
    try:
        authors = await sync_to_async(list)(
            models.Author.objects.filter(id__in=keys)
        )
        author_map = {author.id: author for author in authors}
        return [author_map.get(key) for key in keys]
    except Exception as e:
        logger.error(f"Error loading authors: {e}")
        # Return None for all keys on error
        return [None] * len(keys)
```

Or raise errors for specific keys:

```python title="dataloaders.py"
from strawberry.exceptions import GraphQLError

async def load_authors_strict(keys: List[int]) -> List[models.Author]:
    """Load authors, raising errors for missing ones."""
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=keys)
    )

    author_map = {author.id: author for author in authors}

    result = []
    for key in keys:
        if key not in author_map:
            raise GraphQLError(f"Author with id {key} not found")
        result.append(author_map[key])

    return result
```

## Performance Optimization

### Query Optimization

Minimize database hits in DataLoaders:

```python title="dataloaders.py"
async def load_articles_optimized(
    article_ids: List[int]
) -> List[models.Article]:
    """Load articles with optimized query."""
    articles = await sync_to_async(list)(
        models.Article.objects.filter(id__in=article_ids)
        .select_related('author', 'category')
        .prefetch_related('tags', 'comments')
        .only(
            'id', 'title', 'content', 'author__name',
            'category__name', 'published_date'
        )
    )

    article_map = {article.id: article for article in articles}
    return [article_map.get(key) for key in article_ids]
```

### Caching Strategy

For data that doesn't change often, implement caching:

```python title="dataloaders.py"
from django.core.cache import cache

async def load_categories_cached(category_ids: List[int]) -> List[models.Category]:
    """Load categories with Django cache."""
    # Try to get from cache first
    cache_keys = [f"category:{id}" for id in category_ids]
    cached_data = cache.get_many(cache_keys)

    # Determine which IDs need to be fetched
    categories_by_id = {}
    ids_to_fetch = []

    for i, category_id in enumerate(category_ids):
        cache_key = cache_keys[i]
        if cache_key in cached_data:
            categories_by_id[category_id] = cached_data[cache_key]
        else:
            ids_to_fetch.append(category_id)

    # Fetch missing categories
    if ids_to_fetch:
        categories = await sync_to_async(list)(
            models.Category.objects.filter(id__in=ids_to_fetch)
        )

        # Cache the fetched categories
        to_cache = {
            f"category:{cat.id}": cat
            for cat in categories
        }
        cache.set_many(to_cache, timeout=3600)  # Cache for 1 hour

        for cat in categories:
            categories_by_id[cat.id] = cat

    return [categories_by_id.get(key) for key in category_ids]
```

## Testing DataLoaders

### Unit Testing

```python title="tests/test_dataloaders.py"
import pytest
from ..dataloaders import load_authors
from ..models import Author

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_load_authors():
    # Create test data
    author1 = Author.objects.create(name="Author 1")
    author2 = Author.objects.create(name="Author 2")

    # Test DataLoader
    result = await load_authors([author1.id, author2.id, 999])

    assert len(result) == 3
    assert result[0].id == author1.id
    assert result[1].id == author2.id
    assert result[2] is None  # Non-existent ID


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_dataloader_batching(django_assert_num_queries):
    # Create test data
    authors = [Author.objects.create(name=f"Author {i}") for i in range(5)]

    # DataLoader should batch all loads into a single query
    with django_assert_num_queries(1):
        loader = DataLoader(load_fn=load_authors)
        results = await asyncio.gather(*[
            loader.load(author.id) for author in authors
        ])

    assert len(results) == 5
```

### Integration Testing

```python title="tests/test_graphql.py"
from strawberry_django.test.client import TestClient

def test_author_books_no_n_plus_one(db):
    # Create test data
    author1 = Author.objects.create(name="Author 1")
    author2 = Author.objects.create(name="Author 2")
    Book.objects.create(title="Book 1", author=author1)
    Book.objects.create(title="Book 2", author=author1)
    Book.objects.create(title="Book 3", author=author2)

    client = TestClient("/graphql")

    query = """
        query {
            authors {
                id
                name
                books {
                    id
                    title
                }
            }
        }
    """

    # Should only perform 2 queries: one for authors, one for all books
    with django_assert_num_queries(2):
        result = client.query(query)

    assert result.errors is None
    assert len(result.data["authors"]) == 2
```

## Troubleshooting

### DataLoaders not batching

**Problem**: Each load results in a separate database query.

**Solution**: Ensure you're using ASGI and reusing the same DataLoader instance:

```python
# ❌ Creates new loader each time - no batching
@strawberry.field
async def author(self, info: Info) -> Author:
    loader = DataLoader(load_fn=load_authors)  # New instance!
    return await loader.load(self.author_id)

# ✅ Reuses loader from context - batching works
@strawberry.field
async def author(self, info: Info) -> Author:
    return await info.context.author_loader.load(self.author_id)
```

### "Cannot use DataLoader with sync resolvers"

**Problem**: Mixing sync and async code.

**Solution**: Ensure all resolvers using DataLoaders are async:

```python
# ❌ Sync resolver
@strawberry.field
def author(self, info: Info) -> Author:
    return await info.context.author_loader.load(self.author_id)

# ✅ Async resolver
@strawberry.field
async def author(self, info: Info) -> Author:
    return await info.context.author_loader.load(self.author_id)
```

### DataLoader returns wrong order

**Problem**: Results don't match the order of keys.

**Solution**: Always return results in the same order as the input keys:

```python
async def load_authors(keys: List[int]) -> List[models.Author]:
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=keys)
    )

    # ✅ Create mapping and return in correct order
    author_map = {author.id: author for author in authors}
    return [author_map.get(key) for key in keys]
```

## Best Practices

1. **Store DataLoaders in context** to enable batching across the request
2. **Always return results in key order** from DataLoader functions
3. **Use the Query Optimizer first** - only add DataLoaders when needed
4. **Prefetch related data** in DataLoader queries to avoid nested N+1 issues
5. **Handle missing keys gracefully** by returning `None` or raising clear errors
6. **Test batching behavior** to ensure queries are actually being batched
7. **Keep load functions pure** - avoid side effects in DataLoaders
8. **Use type hints** for better IDE support and type safety

## See Also

- [Query Optimizer](./optimizer.md) - Automatic query optimization
- [Performance](./performance.md) - General performance tips
- [Resolvers](./resolvers.md) - Custom resolver patterns
- [Strawberry DataLoaders Docs](https://strawberry.rocks/docs/guides/dataloaders) - Official Strawberry documentation
