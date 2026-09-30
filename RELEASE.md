---
release type: patch
---

Fix an N+1 query regression when a field declares a `prefetch_related` hint and its resolver returns the prefetched related manager's queryset, for example:

```python
@strawberry_django.type(Author)
class AuthorType:
    @strawberry_django.field(prefetch_related=["books"])
    def books(self) -> list[BookType]:
        return self.books.all()
```

If the related model had no default `Meta.ordering`, the deterministic ordering added in 0.57.0 applied `.order_by("pk")` to the already evaluated queryset. That threw away the prefetched results and ran one extra query per parent. Querysets that have already been evaluated are no longer re-ordered.
