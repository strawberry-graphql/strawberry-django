---
release type: minor
---

Add a `required` argument to `strawberry_django.filter_field`, to make custom filter methods required in the
schema. By default they are optional, as before.

```python
@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    @strawberry_django.filter_field(required=True)
    def search(self, value: str, prefix: str) -> Q:
        return Q(**{f"{prefix}name__icontains": value})
```

```graphql
input FruitFilter {
  search: String!
  ...
}
```
