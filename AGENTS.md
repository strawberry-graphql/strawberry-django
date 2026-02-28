# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`strawberry-graphql-django` — a Django integration for [Strawberry GraphQL](https://github.com/strawberry-graphql/strawberry). It maps Django models to GraphQL types, with automatic field resolution, query optimization, filtering, ordering, pagination, mutations, permissions, and Relay support.

## Commands

```bash
# Install dependencies
uv sync

# Run full test suite
uv run pytest

# Run tests in parallel
uv run pytest -n auto

# Run a single test file
uv run pytest tests/test_optimizer.py -x

# Run a specific test
uv run pytest tests/test_optimizer.py::test_function_name -x

# Lint (ruff check + format check)
uv run ruff check .
uv run ruff format --check .

# Auto-fix lint issues
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run pyright
```

## Architecture

### Core Abstraction: Django Model → GraphQL Type

The central pattern is `@strawberry_django.type(Model)`, which:
1. Introspects `Model._meta.fields` and resolves `strawberry.auto` annotations to concrete GraphQL types (`fields/types.py:resolve_model_field_type`)
2. Wraps every field as a `StrawberryDjangoField` with Django-aware resolution
3. Stores metadata in `StrawberryDjangoDefinition` on `cls.__strawberry_django_definition__`
4. Delegates to `strawberry.type()` internally for the actual GraphQL schema generation

### Field Resolution Chain

`StrawberryDjangoField` (`fields/field.py`) inherits via MRO from mixins that apply in sequence:

```
StrawberryDjangoField
  └─ StrawberryDjangoPagination  (pagination.py — injects pagination args, slices queryset)
      └─ StrawberryDjangoFieldOrdering  (ordering.py — injects order args, applies order_by)
          └─ StrawberryDjangoFieldFilters  (filters.py — injects filter args, applies filter())
              └─ StrawberryDjangoFieldBase  (fields/base.py — auto type mapping, django_getattr)
                  └─ StrawberryField  (upstream strawberry)
```

For list fields, the queryset flows: `get_queryset()` → filters → ordering → pagination → optimizer hints.

### Query Optimizer

`DjangoOptimizerExtension` (`optimizer.py`) is a schema extension that intercepts query execution. It walks the GraphQL selection set and adds `only()`, `select_related()`, `prefetch_related()`, and `annotate()` to querysets based on which fields are selected. Optimization hints are accumulated in `OptimizerStore` instances attached to field definitions via `strawberry_django.field(prefetch_related=..., select_related=..., only=..., annotate=...)`.

### Mutations

`mutations/fields.py` defines `DjangoCreateMutation`, `DjangoUpdateMutation`, `DjangoDeleteMutation` field classes. The actual ORM operations live in `mutations/resolvers.py` (create, update, delete helpers with `full_clean` support). Entry points are `strawberry_django.mutation()` and `strawberry_django.input_mutation()`.

### Key Modules

| Module | Purpose |
|---|---|
| `type.py` | `@type`, `@input`, `@interface`, `@partial` decorators; `_process_type()` central logic |
| `fields/field.py` | `StrawberryDjangoField`, `field()`, `connection()`, `node()`, `offset_paginated()` |
| `fields/base.py` | `StrawberryDjangoFieldBase` — auto type resolution, `django_getattr` |
| `fields/types.py` | Django field → GraphQL type mapping; `DjangoFileType`, input helpers |
| `optimizer.py` | `DjangoOptimizerExtension`, `OptimizerStore` |
| `filters.py` | `filter_type` decorator, `process_filters()`, `FilterLookup` |
| `ordering.py` | `order_type` decorator, `process_order()`, `Ordering` enum |
| `pagination.py` | `OffsetPaginated`, `OffsetPaginationInput`, window pagination |
| `permissions.py` | `HasPerm`, `IsAuthenticated`, `DjangoPermissionExtension` |
| `mutations/` | CRUD mutation fields + ORM resolvers |
| `relay/` | `DjangoCursorConnection`, `DjangoListConnection`, node resolution |
| `resolvers.py` | `django_resolver` decorator — sync/async bridging |
| `settings.py` | `StrawberryDjangoSettings` TypedDict, configured via `settings.STRAWBERRY_DJANGO` |

### Public API

`strawberry_django/__init__.py` re-exports the public surface. Users import as `import strawberry_django` or `from strawberry_django import ...`.

## Testing

- **Framework:** pytest with pytest-django, pytest-asyncio (`asyncio_mode = "auto"`)
- **Database:** in-memory SQLite (spatialite if GEOS available)
- **Settings:** `tests/django_settings.py` (`DJANGO_SETTINGS_MODULE = "tests.django_settings"`)
- **Models:** `tests/models.py` (Fruit, Color, User, Group, Tag, etc.)
- **Test client:** `tests/utils.py:GraphQLTestClient` wraps Django's `Client`/`AsyncClient`; use `assert_num_queries(n)` for query count assertions
- **Parametrized fixtures:** `gql_client` runs each test 4 ways: sync/async × optimizer on/off. The `schema` fixture runs with optimizer on and off.
- **Snapshots:** some tests use pytest-snapshot for schema output assertions

## CI & Releases

- **Matrix:** Django 4.2–6.0 × Python 3.10–3.14 × std/geos modes
- **Type checking:** pyright runs as a separate CI job
- **Release:** This project uses [autopub](https://github.com/autopub/autopub). PRs with releasable changes must include a `RELEASE.md` file at the repo root (CI enforces this). On merge to `main`, autopub reads this file and auto-publishes to PyPI. The file format:

```markdown
---
release type: patch
---

Description of the changes, ideally with examples if adding a new feature.
```

Release type is one of `patch`, `minor`, or `major` per [semver](https://semver.org/).

## Code Style

- Ruff for linting and formatting (`target-version = "py310"`, preview mode enabled)
- No docstring requirements (`D1` ignored)
- Pre-commit hooks: ruff, django-upgrade (target 4.2+), prettier (docs), taplo (TOML)
- Pyright for type checking (`pythonVersion = "3.10"`)
