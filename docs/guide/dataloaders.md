---
title: DataLoaders
---

# DataLoaders

DataLoaders help solve the N+1 query problem by batching and caching database queries. For basic information about DataLoaders, see the [Strawberry DataLoaders documentation](https://strawberry.rocks/docs/guides/dataloaders).

> [!TIP]
> Strawberry Django's [Query Optimizer](./optimizer.md) handles most optimization scenarios automatically. Use DataLoaders when you need custom batching logic or are working with external data sources.

## Using DataLoaders with Django

### Basic Example

Here's a basic DataLoader for fetching Django models:

```python title="dataloaders.py"
from typing import List
from strawberry.dataloader import DataLoader
from asgiref.sync import sync_to_async

from . import models

async def load_authors(keys: List[int]) -> List[models.Author | None]:
    """Batch load authors by their IDs."""
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=keys)
    )

    # Return results in the same order as keys
    author_map = {author.id: author for author in authors}
    return [author_map.get(key) for key in keys]
```

### Sharing DataLoaders Across a Request

**Important**: DataLoaders must be instantiated once per request and shared across all resolvers to enable batching. Store them in the GraphQL context:

```python title="context.py"
from strawberry.dataloader import DataLoader
from .dataloaders import load_authors

class GraphQLContext:
    def __init__(self, request):
        self.request = request
        self._author_loader = None

    @property
    def author_loader(self) -> DataLoader:
        if self._author_loader is None:
            self._author_loader = DataLoader(load_fn=load_authors)
        return self._author_loader

def get_context(request):
    return GraphQLContext(request)
```

```python title="urls.py"
from django.urls import path
from strawberry.django.views import AsyncGraphQLView
from .schema import schema
from .context import get_context

urlpatterns = [
    path('graphql/', AsyncGraphQLView.as_view(
        schema=schema,
        context_getter=get_context
    )),
]
```

### Using the DataLoader

```python title="types.py"
import strawberry_django
from strawberry import field
from strawberry.types import Info

@strawberry_django.type(models.Book)
class Book:
    id: strawberry.auto
    title: strawberry.auto
    author_id: strawberry.Private[int]

    @field
    async def author(self, info: Info) -> "Author":
        return await info.context.author_loader.load(self.author_id)
```

## Common Patterns

### One-to-Many Relationships

```python title="dataloaders.py"
from collections import defaultdict

async def load_books_by_author(author_ids: List[int]) -> List[List[models.Book]]:
    """Load all books for multiple authors."""
    books = await sync_to_async(list)(
        models.Book.objects.filter(author_id__in=author_ids)
    )

    books_by_author = defaultdict(list)
    for book in books:
        books_by_author[book.author_id].append(book)

    return [books_by_author[author_id] for author_id in author_ids]
```

### Many-to-Many Relationships

```python title="dataloaders.py"
async def load_tags(article_ids: List[int]) -> List[List[models.Tag]]:
    """Load tags for multiple articles."""
    articles = await sync_to_async(list)(
        models.Article.objects.filter(id__in=article_ids)
        .prefetch_related('tags')
    )

    tags_by_article = {
        article.id: list(article.tags.all())
        for article in articles
    }

    return [tags_by_article.get(article_id, []) for article_id in article_ids]
```

### Optimizing Queries

Use Django's `select_related()` and `prefetch_related()` in your DataLoaders:

```python title="dataloaders.py"
async def load_authors(keys: List[int]) -> List[models.Author | None]:
    """Load authors with their publisher."""
    authors = await sync_to_async(list)(
        models.Author.objects.filter(id__in=keys)
        .select_related('publisher')
    )

    author_map = {author.id: author for author in authors}
    return [author_map.get(key) for key in keys]
```

## See Also

- [Strawberry DataLoaders Docs](https://strawberry.rocks/docs/guides/dataloaders) - Official Strawberry documentation
- [Query Optimizer](./optimizer.md) - Automatic query optimization
