# Strawberry GraphQL Django Integration

[![CI](https://github.com/strawberry-graphql/strawberry-django/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/strawberry-graphql/strawberry-django/actions/workflows/tests.yml?query=branch%3Amain)
[![Coverage](https://codecov.io/gh/strawberry-graphql/strawberry-django/branch/main/graph/badge.svg)](https://codecov.io/gh/strawberry-graphql/strawberry-django/tree/main)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![Downloads](https://pepy.tech/badge/strawberry-graphql-django)](https://pepy.tech/project/strawberry-graphql-django)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/strawberry-graphql-django)

[**Documentation**](https://strawberry.rocks/docs/django) | [**Discord**](https://strawberry.rocks/discord)

Strawberry GraphQL Django integration provides powerful tools to build GraphQL APIs with Django. Automatically generate GraphQL types, queries, mutations, and resolvers from your Django models with full type safety.

## Installation

```shell
pip install strawberry-graphql-django
```

## Features

- 🍓 **Automatic Type Generation** - Generate GraphQL types from Django models with full type safety
- 🔍 **Advanced Filtering** - Powerful filtering system with lookups (contains, exact, in, etc.)
- 📄 **Pagination** - Built-in offset and cursor-based (Relay) pagination
- 📊 **Ordering** - Sort results by any field with automatic ordering support
- 🔐 **Authentication & Permissions** - Django auth integration with flexible permission system
- ✨ **CRUD Mutations** - Auto-generated create, update, and delete mutations with validation
- ⚡ **Query Optimizer** - Automatic `select_related` and `prefetch_related` to prevent N+1 queries
- 🐍 **Django Integration** - Works with Django views (sync and async), forms, and validation
- 🐛 **Debug Toolbar** - GraphiQL integration with Django Debug Toolbar for query inspection

## Quick Start

```python
# models.py
from django.db import models


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey("Color", on_delete=models.CASCADE, related_name="fruits")


class Color(models.Model):
    name = models.CharField(max_length=20)
```

```python
# types.py
import strawberry_django
from strawberry import auto
from . import models


@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: "Color"


@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: list[Fruit]
```

```python
# schema.py
import strawberry
import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from .types import Fruit


@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()


schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension],
)
```

```python
# urls.py
from django.urls import path
from strawberry.django.views import AsyncGraphQLView
from .schema import schema

urlpatterns = [
    path("graphql/", AsyncGraphQLView.as_view(schema=schema)),
]
```

That's it! You now have a fully functional GraphQL API with:
- Automatic type inference from Django models
- Optimized database queries (no N+1 problems)
- Interactive GraphiQL interface at `/graphql/`

Visit http://localhost:8000/graphql/ and try this query:

```graphql
query {
  fruits {
    id
    name
    color {
      name
    }
  }
}
```

## Next Steps

Check out our comprehensive documentation:

- 📚 [**Getting Started Guide**](https://strawberry.rocks/docs/django) - Complete tutorial with examples
- 🎓 [**Example App**](./examples/ecommerce_app/) - Full-featured e-commerce application
- 📖 [**Documentation**](https://strawberry.rocks/docs/django) - In-depth guides and API reference
- 💬 [**Discord Community**](https://strawberry.rocks/discord) - Get help and share your projects

## Contributing

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated 😊

**Quick Start:**

```shell
git clone https://github.com/strawberry-graphql/strawberry-django
cd strawberry-django
pre-commit install
```

Then run tests with `make test` or `make test-dist` for parallel execution.

## Community

- 💬 [**Discord**](https://strawberry.rocks/discord) - Join our community for help and discussions
- 🐛 [**GitHub Issues**](https://github.com/strawberry-graphql/strawberry-django/issues) - Report bugs or request features
- 💡 [**GitHub Discussions**](https://github.com/strawberry-graphql/strawberry-django/discussions) - Ask questions and share ideas

## License

This project is licensed under the [MIT License](LICENSE).
