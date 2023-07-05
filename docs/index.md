![Logo](./images/logo.png){ align=center }
Strawberry integration with Django.

> makes it easier to build better web apps more quickly and with less code.

---

[![CI](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml/badge.svg)](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![Downloads](https://pepy.tech/badge/strawberry-graphql-django)](https://pepy.tech/project/strawberry-graphql-django)

## Supported features

- [x] GraphQL type generation from models
- [x] Filtering, pagination and ordering
- [x] Basic create, retrieve, update and delete (CRUD) types and mutations
- [x] Basic Django auth support, current user query, login and logout mutations
- [x] Django sync and async views
- [x] Permission extension using django's permissioning system
- [x] Relay support with automatic resolvers generation
- [x] Query optimization to improve performance and avoid common pitfalls (e.g n+1)
- [x] Debug Toolbar integration with graphiql to display metrics like SQL queries
- [x] Unit test integration

## Installation

```sh
pip install strawberry-graphql-django
```

## Basic Usage

```{.python title=models.py}
from django.db import models
from django_choices_field import TextChoicesField

class FruitCategory(models.TextChoices):
    CITRUS = "citrus", "Citrus"
    BERRY = "berry", "Berry"

class Fruit(models.Model):
    """A tasty treat"""
    name = models.CharField(
        max_length=20,
    )
    category = TextChoicesField(
        choices_enum=FruitCategory,
    )
    color = models.ForeignKey(
        "Color",
        on_delete=models.CASCADE,
        related_name="fruits",
        blank=True,
        null=True,
    )

class Color(models.Model):
    name = models.CharField(
        max_length=20,
        help_text="field description",
    )
```

```{.python title=types.py}
import strawberry
from strawberry import auto

from . import models

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    category: auto
    color: "Color"

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: list[Fruit]
```

```{.python title=schema.py}
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

from .types import Fruit

@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry.django.field()

schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
```

```{.python title=settings.py}
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
}
```

```{.python title=urls.py}
from django.urls import include, path
from strawberry.django.views import AsyncGraphQLView

from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```

Code above generates following schema.

```{.graphql title=schema.graphql}
enum FruitCategory {
  CITRUS
  BERRY
}

"""
A tasty treat
"""
type Fruit {
  id: ID!
  name: String!
  category: FruitCategory!
  color: Color
}

type Color {
  id: ID!
  """
  field description
  """
  name: String!
  fruits: [Fruit!]
}

type Query {
  fruits: [Fruit!]!
}
```
