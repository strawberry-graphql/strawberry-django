# Strawberry GraphQL Django extension

[![CI](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml/badge.svg)](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![Downloads](https://pepy.tech/badge/strawberry-graphql-django)](https://pepy.tech/project/strawberry-graphql-django)

This package provides simple and powerful tools to generate GraphQL types, queries, mutations and resolvers from Django models.

Installing `strawberry-graphql-django` package from the python package repository.
```shell
pip install strawberry-graphql-django
```

Full documentation is available under [docs](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/docs/index.md) github folder.


## Supported features

* GraphQL type generation from models
* Filtering, pagination and ordering
* Basic create, retrieve, update and delete (CRUD) types and mutations
* Basic Django auth support, current user query, login and logout mutations
* Django sync and async views
* Unit test integration


## Basic Usage

```python
# models.py
from django.db import models

class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey('Color', blank=True, null=True,
            related_name='fruits', on_delete=models.CASCADE)

class Color(models.Model):
    name = models.CharField(max_length=20)
```

```python
# types.py
import strawberry
from strawberry.django import auto
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

Code above generates following schema.

```schema
type Fruit {
  id: ID!
  name: String!
  color: Color
}

type Color {
  id: ID!
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

See complete Django project from github repository folder [examples/django](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/examples/django).


## Autocompletion with editors

Some editors like VSCode may not be able to resolve symbols and types without explicit `strawberry.django` import. Adding following line to code fixes that problem.

```python
import strawberry.django
```

## Running unit tests
```
poetry install
poetry run pytest
```

## Contributing

We are happy to get pull requests and feedback from you.
