---
release type: minor
---

Add `skip_queryset_filter` parameter to `filter_field()` for declaring virtual (non-filtering) fields on filter types.

Fields marked with `skip_queryset_filter=True` appear in the GraphQL input type but are not applied as database filters. They are accessible via `self.<field>` in custom filter methods, making them useful for passing parameters like thresholds or configuration values.

```python
@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    min_similarity: float | None = strawberry_django.filter_field(
        default=0.3, skip_queryset_filter=True
    )

    @strawberry_django.filter_field
    def filter(self, queryset: QuerySet, prefix: str):
        if self.min_similarity is not None:
            queryset = queryset.annotate(
                similarity=TrigramSimilarity(f"{prefix}name", self.search)
            ).filter(similarity__gte=self.min_similarity)
        return queryset, Q()
```
