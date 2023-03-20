![Logo](./images/logo.png){ align=center }
Strawberry integration with Django.

> makes it easier to build better web apps more quickly and with less code.

---

[![CI](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml/badge.svg)](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![Downloads](https://pepy.tech/badge/strawberry-graphql-django)](https://pepy.tech/project/strawberry-graphql-django)

## Supported features:

- [x] GraphQL type generation from models
- [x] Filtering, pagination and ordering
- [x] Basic create, retrieve, update and delete (CRUD) types and mutations
- [x] Basic Django auth support, current user query, login and logout mutations
- [x] Django sync and async views
- [x] Unit test integration
- [x] [Django Debug Toolbar integration](./guides/debug-toolbar.md) with graphiql to display metrics like SQL queries

## Installation

```python
pip install strawberry-graphql-django
```

## Basic Usage

```python
# models.py
from django.db import models

class Fruit(models.Model):
    """A tasty treat"""
    name = models.CharField(max_length=20)
    color = models.ForeignKey('Color', blank=True, null=True,
            related_name='fruits', on_delete=models.CASCADE)

class Color(models.Model):
    name = models.CharField(
        max_length=20,
        help_text="field description",
    )
```

```python
# types.py
import strawberry
from strawberry import auto
from typing import List
from . import models

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: 'Color'

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: List[Fruit]
```

```python
# schema.py
import strawberry
from typing import List
from .types import Fruit

@strawberry.type
class Query:
    fruits: List[Fruit] = strawberry.django.field()

schema = strawberry.Schema(query=Query)
```

```python
# settings.py
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
}
```

Code above generates following schema.

```schema
"""
A tasty treat
"""
type Fruit {
  id: ID!
  name: String!
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

```python
# urls.py
from django.urls import include, path
from strawberry.django.views import AsyncGraphQLView
from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```
