---
release type: patch
---

Connection resolvers can now be annotated with a `QuerySet[Model]` return type
instead of being forced to widen it to `Iterable[Model]`:

```python
@strawberry_django.connection(DjangoCursorConnection[FruitType])
@staticmethod
def fruits() -> QuerySet[Fruit]:
    return Fruit.objects.all()
```

Previously this raised `RelayWrongResolverAnnotationError` because Django's
`QuerySet[Model]` collapses to the bare `QuerySet` class, which the relay
annotation check did not recognize as iterable.
