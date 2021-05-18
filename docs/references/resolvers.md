# Resolvers

Basic resolvers are generated automatically. Developer just need to define the type and library handles the rest.

However it is possible to overwrite them by writing own resolvers.

## Sync resolvers
```python
@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry_django.field
    def fruits(self) -> List[Fruit]:
        return self.fruits.objects.filter(...)
```

## Async resolvers
```python
from asgiref.sync import sync_to_async

@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto

    @strawberry_django.field
    async def fruits(self) -> List[Fruit]:
        @sync_to_async
        def query():
            return list(self.fruits.objects.filter(...))
        return query()
```
