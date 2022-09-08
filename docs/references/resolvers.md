# Resolvers

Basic resolvers are generated automatically once the types are declared.

However it is possible to override them with custom resolvers.

## Sync resolvers

```python
# types.py
from strawberry import auto
from typing import List
from . import models

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry.django.field
    def fruits(self) -> List[Fruit]:
        return self.fruits.objects.filter(...)
```

## Async resolvers

```python
# types.py
from strawberry import auto
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

It is important to note that overriding resolvers also removes default capabilities
(e.g. `Pagination`, `Filter`). On your root `Query`, you can use a custom `get_queryset` to achieve
similar results, but note that it will affect all root queries for that type.

For example, if we wanted a query for berries and one for non-berry fruits, we could do the following:

```python
# types.py
import strawberry
import strawberry_django
from strawberry.django import auto
from typing import List
from . import models

@strawberry.django.type(models.Fruit, is_interface=True)
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
