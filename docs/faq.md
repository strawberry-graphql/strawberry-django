---
title: Frequently Asked Questions
---

# Frequently Asked Questions (FAQ)

## General Usage

### How to access Django request object in resolvers?

The request object is accessible via the `get_request` method.

```python
from strawberry_django.utils.requests import get_request
from strawberry.types import Info

def resolver(root, info: Info):
    request = get_request(info)
    # Access request properties
    user = request.user
    headers = request.headers
```

### How to access the current user object in resolvers?

The current user object is accessible via the `get_current_user` method.

```python
from strawberry_django.auth.utils import get_current_user
from strawberry.types import Info

def resolver(root, info: Info):
    current_user = get_current_user(info)
    if current_user.is_authenticated:
        # Do something with authenticated user
        pass
```

### Where can I find example projects?

Check out the [examples directory](https://github.com/strawberry-graphql/strawberry-django/tree/main/examples) in the GitHub repository for complete Django project examples.

## IDE and Development

### Type checking errors with strawberry.auto

If your type checker (PyLance, mypy) shows errors with `strawberry.auto`, it's because you're returning a Django model instance while the annotation expects a GraphQL type. Use type casts to inform the type checker that the return value is compatible:

```python
from typing import cast

@strawberry_django.mutation
def create_fruit(self, name: str) -> Fruit:  # Fruit is the GraphQL type
    fruit = models.Fruit.objects.create(name=name)  # Returns Django model
    return cast(Fruit, fruit)  # Tell type checker: model is compatible with GraphQL type
```

This is only needed when the annotation is a GraphQL type but you're returning a Django model instance. The cast is purely for type checking and has no runtime effect.

## Queries and Optimization

### Should I use the Query Optimizer or DataLoaders?

**Use the [Query Optimizer](guide/optimizer.md)** (recommended for most cases):

- Automatic optimization
- Works with Django ORM
- Less code to maintain
- Handles most N+1 scenarios

```python
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension],
)
```

**Use DataLoaders** when:

- You need custom batching logic
- Fetching from external APIs
- The optimizer doesn't handle your use case
- You need fine-grained caching control

See [DataLoaders guide](./guide/dataloaders.md) for details.

### How do I avoid N+1 queries?

Three main approaches:

1. **Enable the Query Optimizer** (easiest):

```python
schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension],
)
```

2. **Add optimization hints** to custom fields:

```python
@strawberry_django.field(
    select_related=["author"],
    prefetch_related=["tags"]
)
def custom_field(self, root) -> str:
    return f"{root.author.name}: {root.tags.count()}"
```

3. **Use DataLoaders** for complex scenarios (see above).

### How do I filter on related model fields?

Define nested filter types:

```python
@strawberry_django.filter_type(models.Author)
class AuthorFilter:
    name: auto

@strawberry_django.filter_type(models.Book)
class BookFilter:
    title: auto
    author: AuthorFilter | None
```

Query:

```graphql
query {
  books(filters: { author: { name: "John" } }) {
    title
    author {
      name
    }
  }
}
```

### Can I use annotated/computed fields in filters and ordering?

Yes, use custom filter/order methods:

```python
from django.db.models import Count, Q, QuerySet

@strawberry_django.filter_type(models.Author)
class AuthorFilter:
    name: auto

    @strawberry_django.filter_field
    def book_count(
        self,
        queryset: QuerySet,
        value: int,
        prefix: str
    ) -> tuple[QuerySet, Q]:
        queryset = queryset.alias(
            _book_count=Count(f"{prefix}books")
        )
        return queryset, Q(**{f"{prefix}_book_count": value})
```

## Mutations

### How do I create nested objects in mutations?

**Recommended**: Use the automatic mutation generators which handle nested relationships automatically:

```python
import strawberry
import strawberry_django
from strawberry_django import mutations
from . import models

@strawberry_django.input(models.Author)
class AuthorInput:
    name: auto
    books: auto  # Automatically handles nested book creation

@strawberry.type
class Mutation:
    create_author: Author = mutations.create(AuthorInput)
    update_author: Author = mutations.update(AuthorInput)
    delete_author: Author = mutations.delete()
```

These mutations automatically:

- Generate appropriate input types for nested relationships
- Handle create, update, and delete operations on related objects
- Validate data using Django's validation system

See the [tests in the repository](https://github.com/strawberry-graphql/strawberry-django/tree/main/tests) for complete examples of automatic mutations with nested relationships.

**Manual approach** (when you need custom logic):

```python
from django.db import transaction

@strawberry_django.input(models.Author)
class AuthorInputWithBooks:
    name: auto
    email: auto
    books: list[BookInput] | None = None

@strawberry_django.mutation(handle_django_errors=True)
@transaction.atomic
def create_author_with_books(self, data: AuthorInputWithBooks) -> Author:
    author = models.Author.objects.create(
        name=data.name,
        email=data.email
    )

    if data.books:
        for book_data in data.books:
            models.Book.objects.create(
                author=author,
                title=book_data.title,
            )

    return models.Author.objects.get(pk=author.pk)
```

See [Nested Mutations guide](./guide/nested-mutations.md) for more details.

### How do I update many-to-many relationships?

Use `ListInput` with `set`, `add`, or `remove` operations:

```python
from strawberry_django import ListInput, NodeInput

@strawberry_django.partial(models.Article)
class ArticleInputPartial(NodeInput):
    title: auto
    tags: ListInput[strawberry.ID] | None = None

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

### Why don't related objects appear in my mutation response?

Django caches related managers. Refresh or refetch the object:

```python
@strawberry_django.mutation
@transaction.atomic
def create_with_relations(self, data: Input) -> Model:
    obj = models.Model.objects.create(...)
    # Create related objects...

    # ✅ Option 1: Refresh
    obj.refresh_from_db()

    # ✅ Option 2: Refetch (better for optimizer)
    return models.Model.objects.get(pk=obj.pk)
```

### How do I handle validation errors properly?

Use dict-style `ValidationError` for field-specific errors:

```python
from django.core.exceptions import ValidationError

@strawberry_django.mutation(handle_django_errors=True)
def create_user(self, email: str, age: int) -> User:
    errors = {}

    if not email or "@" not in email:
        errors["email"] = "Invalid email address"

    if age < 18:
        errors["age"] = "Must be at least 18 years old"

    if errors:
        raise ValidationError(errors)

    return models.User.objects.create(email=email, age=age)
```

See [Error Handling guide](./guide/error-handling.md) for details.

## Permissions and Authentication

### How do I protect fields based on permissions?

Use permission extensions:

```python
from strawberry_django.permissions import IsAuthenticated, HasPerm

@strawberry_django.type(models.Document)
class Document:
    title: auto

    @strawberry_django.field(extensions=[IsAuthenticated()])
    def content(self) -> str:
        return self.content

    @strawberry_django.field(extensions=[HasPerm("documents.view_secret")])
    def secret_data(self) -> str:
        return self.secret
```

See [Permissions guide](./guide/permissions.md) for more options.

### Can I use Django's object-level permissions?

Yes, with django-guardian:

```python
from strawberry_django.permissions import HasRetvalPerm

@strawberry_django.type(models.Document)
class Document:
    @strawberry_django.field(
        extensions=[HasRetvalPerm("documents.view_document")]
    )
    def content(self) -> str:
        # Permission checked against this specific document instance
        return self.content
```

See [Guardian integration](./integrations/guardian.md).

## Types and Fields

### How do I use custom Django field types?

Map them in the `field_type_map`:

```python
from strawberry_django.fields.types import field_type_map
from django.db import models
import strawberry

# For django-money
from djmoney.models.fields import MoneyField
MoneyScalar = strawberry.scalar(...)

field_type_map.update({
    MoneyField: MoneyScalar,
    models.SlugField: str,
})
```

### How do I add computed fields to my types?

Three options:

1. **Model property** (recommended):

```python
from decimal import Decimal
from strawberry_django.descriptors import model_property

class Order(models.Model):
    price = models.DecimalField(...)
    quantity = models.IntegerField(...)

    @model_property(only=["price", "quantity"])
    def total(self) -> Decimal:
        return self.price * self.quantity
```

2. **Custom resolver**:

```python
from decimal import Decimal

@strawberry_django.type(models.Order)
class Order:
    price: auto
    quantity: auto

    @strawberry_django.field(only=["price", "quantity"])
    def total(self) -> Decimal:
        return self.price * self.quantity
```

3. **Annotated field**:

```python
from django.db.models import F

@strawberry_django.type(models.Order)
class Order:
    price: auto
    quantity: auto
    total: auto = strawberry_django.field(
        annotate={"total": F("price") * F("quantity")}
    )
```

See [Model Properties guide](./guide/model-properties.md) for details.

### How do I work with Django's choices fields?

Use [django-choices-field](./integrations/choices-field.md):

```python
from django_choices_field import TextChoicesField

class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"

class Company(models.Model):
    status = TextChoicesField(choices_enum=Status)
```

This automatically generates GraphQL enums.

## Relay and Global IDs

### How do I use Relay-style pagination?

```python
import strawberry
from strawberry import relay
import strawberry_django

@strawberry_django.type(models.Fruit)
class Fruit(relay.Node):
    name: auto

@strawberry.type
class Query:
    fruits: relay.Connection[Fruit] = strawberry_django.connection()
```

See [Relay guide](./guide/relay.md).

### Should I use offset or cursor pagination?

**Offset pagination** (default):

- Straightforward to implement
- Allows jumping to any page
- Works well for small to medium datasets

**Cursor pagination**:

- Better performance for large datasets
- Prevents missing/duplicate items during pagination
- Required for Relay compliance

Choose based on your use case and dataset size.

## Testing

### How do I test GraphQL mutations and queries?

Use the test client:

```python
from strawberry_django.test.client import TestClient

def test_create_fruit(db):
    client = TestClient("/graphql")

    res = client.query("""
        mutation {
            createFruit(data: { name: "Apple" }) {
                id
                name
            }
        }
    """)

    assert res.errors is None
    assert res.data["createFruit"]["name"] == "Apple"
```

For authenticated tests:

```python
def test_authenticated_query(db):
    user = User.objects.create_user(username="test")
    client = TestClient("/graphql")

    with client.login(user):
        res = client.query("query { me { username } }")

    assert res.data["me"]["username"] == "test"
```

See [Unit Testing guide](./guide/unit-testing.md).

### How do I test async resolvers?

Use `pytest-asyncio`:

```python
import pytest

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_async_resolver():
    result = await my_async_resolver()
    assert result is not None
```

## Advanced Topics

### Can I use Federation with Strawberry Django?

Yes, but it requires additional setup. Check the [Federation guide](https://strawberry.rocks/docs/guides/federation) in Strawberry's documentation.

### How do I handle file uploads?

Use Strawberry's `Upload` scalar:

```python
from strawberry.file_uploads import Upload

@strawberry.type
class Mutation:
    @strawberry_django.mutation
    def upload_file(self, file: Upload) -> bool:
        content = file.read()
        # Handle the file...
        return True
```

## Common Errors

### "Object has no attribute 'refresh_from_db'"

You're likely returning a non-model object. Ensure you're returning actual Django model instances:

```python
# ❌ Returns dict
return {"id": obj.id, "name": obj.name}

# ✅ Returns model instance
return obj
```

### "Interface cannot be part of Union"

This happens when using interfaces with `handle_django_errors=True`. Either:

1. Return concrete types:

```python
update_project: WebProject | ExternalProject = mutations.update_project(...)
```

2. Or disable error handling:

```python
update_project: Project = mutations.update_project(handle_django_errors=False)
```

## Getting More Help

- **Documentation**: Check the [full guides](./guide/)
- **Troubleshooting**: See [Troubleshooting guide](./guide/troubleshooting.md)
- **GitHub Issues**: [Search existing issues](https://github.com/strawberry-graphql/strawberry-django/issues)
- **Discussions**: [GitHub Discussions](https://github.com/strawberry-graphql/strawberry-django/discussions)
- **Discord**: [Join the Strawberry Discord](https://strawberry.rocks/discord)
