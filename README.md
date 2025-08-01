# Strawberry GraphQL Django integration

[![CI](https://github.com/strawberry-graphql/strawberry-django/actions/workflows/tests.yml/badge.svg)](https://github.com/strawberry-graphql/strawberry-django/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/strawberry-graphql/strawberry-django/branch/main/graph/badge.svg?token=JNH6PUYh3e)](https://codecov.io/gh/strawberry-graphql/strawberry-django)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![Downloads](https://pepy.tech/badge/strawberry-graphql-django)](https://pepy.tech/project/strawberry-graphql-django)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/strawberry-graphql-django)

[**Docs**](https://strawberry.rocks/docs/django) | [**Discord**](https://strawberry.rocks/discord)

This package provides powerful tools to generate GraphQL types, queries,
mutations and resolvers from Django models.

Installing `strawberry-graphql-django` package from the python package repository.

```shell
pip install strawberry-graphql-django
```

## Supported Features

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

## Basic Usage

```python
# models.py

from django.db import models

class Fruit(models.Model):
    """A tasty treat"""
    name = models.CharField(
        max_length=20,
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

```python
# types.py

import strawberry_django
from strawberry import auto

from . import models

@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: 'Color'

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
    extensions=[
        DjangoOptimizerExtension,  # not required, but highly recommended
    ],
)
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

Code above generates following schema.

```graphql
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

## Contributing

We use [poetry](https://github.com/sdispater/poetry) to manage dependencies, to
get started follow these steps:

```shell
$ git clone https://github.com/strawberry-graphql/strawberry-django
$ cd strawberry-django
$ python -m pip install poetry
$ make install
```

### Running tests

Using [make](Makefile) to run the tests:

```shell
$ make test
```

To run tests in parallel:

```shell
$ make test-dist
```

### Pre commit

We have a configuration for
[pre-commit](https://github.com/pre-commit/pre-commit), to add the hook run the
following command:

```shell
pre-commit install
```
