<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

![Logo](./images/logo.png){ align=center }
**Strawberry integration with Django**

---

**WHAT:** A toolset for GraphQL schema generation from Django models.

**WHY:** To build better web apps more quickly and with less code.

**HOW:** By providing django-specific methods for using the [strawberry GraphQL library](https://strawberry.rocks/).

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

## Getting started

Check out the [quick start](quick-start.md) for all the basics, then the [example app](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/examples/django) for a slightly more complete setup
)
