---
title: Resolvers
---

# Custom Resolvers

Basic resolvers are generated automatically once the types are declared.

However it is possible to override them with custom resolvers.

## Sync resolvers

Sync resolvers can be used in both ASGI/WSGI and will be automatically wrapped
in `sync_to_async` when running async.

```python title="types.py"
import strawberry_django
from strawberry import auto
from . import models

@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry_django.field
    def fruits(self) -> list[Fruit]:
        return self.fruits.objects.filter(...)
```

## Async resolvers

Async resolvers can be used when running using ASGI.

```python title="types.py"
import strawberry_django
from strawberry import auto
from . import models
from asgiref.sync import sync_to_async

@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry_django.field
    async def fruits(self) -> list[Fruit]:
        return sync_to_async(list)(self.fruits.objects.filter(...))
```

## Optimizing resolvers

When using custom resolvers together with the [Query Optimizer Extension](optimizer.md)
you might need to give it a "hint" on how to optimize that field

Take a look at the [optimization hints](optimizer.md#optimization-hints)
docs for more information about this topic.

## Issues with Resolvers

It is important to note that overriding resolvers also removes default capabilities
(e.g. `Pagination`, `Filter`), exception for [relay connections](relay.md). You can
however still add those by hand and resolve them:

```python title="types.py"
import strawberry
from strawberry import auto
from strawberry.types import Info
import strawberry_django
from . import models


@strawberry_django.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit, order=FruitOrder)
class Fruit:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit, is_interface=True)
class Fruit:
    id: auto
    name: auto


@strawberry.type
class Query:
    @strawberry_django.field
    def fruits(
        self,
        filters: FruitFilter | None = strawberry.UNSET,
        order: FruitOrder | None = strawberry.UNSET,
        info: Info
    ) -> list[Fruit]
        qs = models.fruit.objects.all()

        # apply filters if defined
        if filters is not strawberry.UNSET:
            qs = strawberry_django.filters.apply(filters, qs, info)

        # apply ordering if defined
        if order is not strawberry.UNSET:
            qs = strawberry_django.ordering.apply(filters, qs)

        return qs
```
