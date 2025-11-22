---
title: Troubleshooting
---

# Troubleshooting

This guide covers common issues encountered when using Strawberry Django and their solutions.

## Installation and Setup Issues

### Import Errors

**Problem**: `Cannot find reference 'django' in 'strawberry_django'`

**Solution**: This is typically an IDE issue (PyCharm, VS Code). Add this import to help your IDE:

```python
import strawberry.django  # Helps IDE resolve strawberry_django imports
import strawberry_django
```

### Module Not Found

**Problem**: `ModuleNotFoundError: No module named 'strawberry_django'`

**Solution**: Ensure the package is installed:

```bash
pip install strawberry-graphql-django
# or
poetry add strawberry-graphql-django
```

## Type and Field Resolution

### Auto Type Resolution Fails

**Problem**: `strawberry.auto` doesn't resolve the correct type.

**Solution**: Define custom type mapping for non-standard Django fields:

```python
from strawberry_django.fields.types import field_type_map
from django.db import models
import strawberry

# Map custom Django field to GraphQL type
field_type_map.update({
    models.SlugField: str,
    models.JSONField: strawberry.scalars.JSON,
})
```

See [Fields - Defining types for auto fields](./fields.md#defining-types-for-auto-fields) for more details.

### Forward Reference Errors

**Problem**: `NameError: name 'SomeType' is not defined`

**Solution**: Use string annotations for forward references:

```python
@strawberry_django.type(models.Author)
class Author:
    id: auto
    name: auto
    books: list["Book"]  # String reference, not Book

@strawberry_django.type(models.Book)
class Book:
    id: auto
    title: auto
    author: "Author"  # String reference
```

### Type Annotation Issues with Ordering

**Problem**: `TypeError: unsupported operand type(s) for |: 'str' and 'NoneType'`

**Solution**: This occurs with self-referential ordering in Python 3.13+. Use `Optional` or proper forward references:

```python
from typing import Optional

@strawberry_django.order_type(models.User)
class UserOrder:
    name: auto
    # ❌ creator: "UserOrder"  # Fails in Python 3.13+
    creator: Optional["UserOrder"] = None  # ✅ Works
```

## Query Optimization

### N+1 Query Problems

**Problem**: Multiple database queries are executed for related objects.

**Solution 1**: Enable the Query Optimizer Extension (recommended):

```python title="schema.py"
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension],
)
```

**Solution 2**: Use DataLoaders for custom batching:

See [DataLoaders guide](./dataloaders.md) for details.

**Solution 3**: Add optimization hints to model properties:

```python
from strawberry_django.descriptors import model_property

@model_property(select_related=["author"], only=["author__name"])
def author_name(self) -> str:
    return self.author.name
```

### Annotated Fields Not Working in Nested Queries

**Problem**: Annotations defined with `strawberry_django.field(annotate=...)` don't work in nested queries.

**Cause**: The optimizer may not apply annotations correctly in deeply nested contexts.

**Solution**: Use model-level annotations or custom DataLoaders:

```python
@model_property(
    annotate={"_book_count": Count("books")}
)
def book_count(self) -> int:
    return self._book_count  # type: ignore
```

### Deferred Field Access Issues

**Problem**: Accessing a field triggers extra queries even with optimizer enabled.

**Solution**: Add `only` hints to custom fields and model properties:

```python
@strawberry_django.field(only=["price", "quantity"])
def total(self, root) -> Decimal:
    return root.price * root.quantity
```

## Mutations and Relationships

### Related Objects Not Appearing in Mutation Response

**Problem**: After creating related objects in a mutation, they don't appear in the response.

**Cause**: Django caches the related manager before the objects are created.

**Solution**: Refresh the object or fetch it again:

```python
@strawberry_django.mutation
@transaction.atomic
def create_author_with_books(self, data: AuthorInput) -> Author:
    author = models.Author.objects.create(name=data.name)

    for book in data.books:
        models.Book.objects.create(author=author, **book)

    # ✅ Option 1: Refresh from database
    author.refresh_from_db()

    # ✅ Option 2: Fetch again (better for optimizer)
    # return models.Author.objects.get(pk=author.pk)

    return author
```

### ListInput Not Updating Many-to-Many Relations

**Problem**: Using `ListInput` with `set`, `add`, or `remove` doesn't update relationships.

**Solution**: Ensure you're using the correct field type and handling the operations:

```python
@strawberry_django.partial(models.Article)
class ArticleInputPartial(NodeInput):
    title: auto
    tags: ListInput[strawberry.ID] | None = None  # ✅ ListInput for M2M

@strawberry_django.mutation
def update_article(self, data: ArticleInputPartial) -> Article:
    article = models.Article.objects.get(pk=data.id)

    if data.tags is not strawberry.UNSET and data.tags is not None:
        if data.tags.set is not None:
            article.tags.set(data.tags.set)
        if data.tags.add is not None:
            article.tags.add(*data.tags.add)
        if data.tags.remove is not None:
            article.tags.remove(*data.tags.remove)

    article.save()
    return article
```

See [Nested Mutations guide](./nested-mutations.md) for comprehensive examples.

### Polymorphic Models in ListInput

**Problem**: Updating M2M with polymorphic models removes objects incorrectly.

**Cause**: Concrete model instances aren't matched with abstract base model instances in the existing set.

**Workaround**: Use `InheritanceManager` with proper subclass selection:

```python
from model_utils.managers import InheritanceManager

class Project(models.Model):
    # ...
    objects = InheritanceManager()
```

Then ensure relationships use `select_subclasses()`:

```python
existing = set(manager.select_subclasses() if isinstance(manager, InheritanceManager) else manager.all())
```

See [GitHub Issue #793](https://github.com/strawberry-graphql/strawberry-django/issues/793) for details.

### Validation Errors Not Showing Field Information

**Problem**: Validation errors don't indicate which field failed.

**Solution**: Use Django's dict-style ValidationError:

```python
from django.core.exceptions import ValidationError

# ❌ No field info
raise ValidationError("Invalid email")

# ✅ With field info
raise ValidationError({'email': 'Invalid email address'})

# ✅ Multiple fields
raise ValidationError({
    'email': 'Invalid email address',
    'age': 'Must be at least 18'
})
```

## Permissions and Authentication

### Permission Extensions Not Working

**Problem**: Permission checks are not enforced.

**Cause**: Extensions may not be properly configured or the user context isn't set.

**Solution**: Ensure proper setup:

```python
# 1. Check extension is added to the field
@strawberry_django.field(extensions=[IsAuthenticated()])
def sensitive_data(self) -> str:
    return self.data

# 2. Ensure Django middleware is configured
MIDDLEWARE = [
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ...
]

# 3. For async views, use AuthGraphQLProtocolTypeRouter
from strawberry_django.routers import AuthGraphQLProtocolTypeRouter
```

### Getting Current User Returns None

**Problem**: `get_current_user(info)` returns `None` even when authenticated.

**Solution**: Check request setup:

```python
from strawberry_django.auth.utils import get_current_user

def resolver(self, info: Info):
    request = info.context.request
    print(f"Authenticated: {request.user.is_authenticated}")  # Debug
    user = get_current_user(info)
    return user
```

Ensure authentication middleware is properly configured and the view is set up correctly.

## Filters and Ordering

### DISTINCT Filter Causing Wrong totalCount

**Problem**: Using `DISTINCT=true` in filters returns incorrect `totalCount` in connections.

**Cause**: COUNT queries with DISTINCT on joined tables can produce incorrect results.

**Workaround**: Use a subquery or custom totalCount resolver:

```python
@strawberry.field
def total_count(self, root) -> int:
    # Custom count logic that handles DISTINCT properly
    return root.values('pk').distinct().count()
```

### Filter on Relationships Not Working

**Problem**: Filtering by related model fields doesn't work.

**Solution**: Ensure the filter relationship chain is correct:

```python
@strawberry_django.filter_type(models.Color)
class ColorFilter:
    id: auto
    name: auto

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
    color: ColorFilter | None  # ✅ Proper relationship filter
```

Query with correct nesting:

```graphql
query {
  fruits(filters: { color: { name: "red" } }) {
    id
    name
  }
}
```

### Ordering Not Respecting Variable Order

**Problem**: Multiple ordering fields don't respect the order specified in variables.

**Cause**: Dict ordering may not be preserved in some Python versions or implementations.

**Solution**: Use a list of ordering inputs with the new `@strawberry_django.order_type`:

```python
@strawberry_django.order_type(models.Fruit)
class FruitOrder:
    name: auto
    created: auto
```

Query:

```graphql
query {
  fruits(ordering: [{ name: ASC }, { created: DESC }]) {
    id
    name
  }
}
```

## Relay and Global IDs

### Global ID Mapping Not Working

**Problem**: `auto` fields for IDs aren't mapped to `GlobalID` even with `MAP_AUTO_ID_AS_GLOBAL_ID=True`.

**Solution**: Ensure the setting is properly configured and types inherit from `relay.Node`:

```python title="settings.py"
STRAWBERRY_DJANGO = {
    "MAP_AUTO_ID_AS_GLOBAL_ID": True,
}
```

```python title="types.py"
from strawberry.relay import Node

@strawberry_django.type(models.Fruit)
class Fruit(Node):  # ✅ Inherit from Node
    id: auto  # Will be mapped to GlobalID
    name: auto
```

### Custom Node Resolver Not Working

**Problem**: Custom `resolve_node` logic isn't being called.

**Solution**: Ensure you're overriding the correct method:

```python
from strawberry.relay import Node

@strawberry_django.type(models.Fruit)
class Fruit(Node):
    @classmethod
    def resolve_id(cls, root, info) -> strawberry.ID:
        # Custom ID resolution
        return strawberry.ID(f"custom_{root.pk}")

    @classmethod
    def resolve_nodes(cls, info, node_ids, required=False):
        # Custom node fetching
        return models.Fruit.objects.filter(pk__in=node_ids)
```

## Subscriptions

### Subscriptions Not Working

**Problem**: Websocket connections fail or subscriptions don't receive updates.

**Solution**: Ensure proper ASGI and channels setup:

```python title="asgi.py"
import os
from django.core.asgi import get_asgi_application
from strawberry_django.routers import AuthGraphQLProtocolTypeRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_asgi_app = get_asgi_application()

from .schema import schema

application = AuthGraphQLProtocolTypeRouter(
    schema,
    django_application=django_asgi_app,
)
```

```python title="settings.py"
INSTALLED_APPS = [
    'daphne',  # Must be before 'django.contrib.staticfiles'
    'django.contrib.staticfiles',
    # ...
]

ASGI_APPLICATION = 'project.asgi.application'
```

## Testing

### Async Test Failures

**Problem**: `RuntimeError: no running event loop` in async tests.

**Solution**: Use `pytest-asyncio` and mark tests properly:

```python
import pytest

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_async_resolver():
    result = await some_async_function()
    assert result is not None
```

### Test Client Authentication Not Working

**Problem**: Authentication doesn't persist in test client.

**Solution**: Use the login context manager:

```python
from strawberry_django.test.client import TestClient

def test_authenticated_query(db):
    user = User.objects.create_user(username='test')
    client = TestClient("/graphql")

    with client.login(user):  # ✅ Use context manager
        res = client.query("""
            query {
                me {
                    username
                }
            }
        """)

    assert res.data["me"]["username"] == "test"
```

## Performance Issues

### Slow Queries with Large Datasets

**Problem**: Queries are slow with large result sets.

**Solutions**:

1. **Enable pagination**:

```python
@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto
```

2. **Use cursor-based pagination** for very large datasets:

```python
from strawberry_django.relay import DjangoCursorConnection

@strawberry.type
class Query:
    fruits: DjangoCursorConnection[Fruit] = strawberry_django.connection()
```

3. **Add database indexes** to filtered/ordered fields:

```python
class Fruit(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    created = models.DateTimeField(db_index=True)
```

### Memory Issues with Large Responses

**Problem**: Server runs out of memory with large queries.

**Solution**: Implement pagination limits and use streaming:

```python title="settings.py"
STRAWBERRY_DJANGO = {
    "PAGINATION_DEFAULT_LIMIT": 100,  # Limit results
}
```

## IDE and Type Checking

### PyLance/Mypy Type Errors

**Problem**: Type checker shows errors on `strawberry.auto` or casts.

**Solution**: Use proper type annotations and casts:

```python
from typing import cast

@strawberry_django.mutation
def create_fruit(self, name: str) -> Fruit:
    fruit = models.Fruit.objects.create(name=name)
    return cast(Fruit, fruit)  # ✅ Help type checker
```

### VS Code Auto-Import Not Working

**Problem**: Auto-import doesn't suggest `strawberry_django` imports.

**Solution**: Add explicit import at top of module:

```python
import strawberry.django  # Helps VS Code
import strawberry_django
```

## Getting Help

If your issue isn't covered here:

1. **Check existing issues**: Search [GitHub Issues](https://github.com/strawberry-graphql/strawberry-django/issues)
2. **Check discussions**: Look at [GitHub Discussions](https://github.com/strawberry-graphql/strawberry-django/discussions)
3. **Join Discord**: Ask in the [Strawberry Discord](https://strawberry.rocks/discord)
4. **Review examples**: Check the [example app](https://github.com/strawberry-graphql/strawberry-django/tree/main/examples/django)
5. **Enable debug logging**: Add logging to see what's happening:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('strawberry_django')
logger.setLevel(logging.DEBUG)
```

## See Also

- [Error Handling](./error-handling.md) - Handling errors in mutations
- [Query Optimizer](./optimizer.md) - Understanding query optimization
- [DataLoaders](./dataloaders.md) - Advanced data loading patterns
- [FAQ](../faq.md) - Frequently asked questions
