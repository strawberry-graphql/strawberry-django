# Resolvers

Basic resolvers are generated automatically. Developer need to define the type and library handles the rest.

However it is possible to overwrite them by writing own resolvers.

## Sync resolvers

```python
#types.py

from strawberry.django import auto
from typing import List
from . import models

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry_django.field
    def fruits(self) -> List[Fruit]:
        return self.fruits.objects.filter(...)
```

## Async resolvers

```python
#types.py

from strawberry.django import auto
from typing import List
from . import models
from asgiref.sync import sync_to_async

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry.django.field
    async def fruits(self) -> List[Fruit]:
        @sync_to_async
        def query():
            return list(self.fruits.objects.filter(...))
        return query()
```

## Issues with Resolvers

It is important that if you override resolvers, you will lose access to all of the things that come by default
with the library (e.g. `Pagination`, `Filter`). For Types that are attached to your base `Query`, it
is recommended to define a custom `get_queryset` on the Type
(see [Django Model Types](django_model_types.md) for details).

For example, if we wanted a look up for berries and one for non-berry fruits.

```python

#types.py

import strawberry
import strawberry_django
from strawberry.django import auto
from typing import List
from . import models

@strawberry.django.types(models.Fruit, interface=True)
class Fruit:
    id: auto
    name: auto


@strawberry.django.type(models.Fruit)
class Berry(Fruit):
    def get_queryset(self, queryset, info):
        return queryset.filter(name__contains="berry")


@strawberry.django.type(models.Fruit)
class NonBerry(Fruit):
    def get_queryset(self, queryset, info):
        return queryset.exclude(name__contains="berry")


@strawberry.type
class Query:
    berries: List[Berry]
    non_berries: List[NonBerry]
```
