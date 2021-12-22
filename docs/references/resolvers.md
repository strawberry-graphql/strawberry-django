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
