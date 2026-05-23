---
release type: minor
---

`DateFilterLookup`, `TimeFilterLookup` and `DatetimeFilterLookup` no longer require a type parameter, matching `StrFilterLookup`. The generated GraphQL input names also lose their type prefix (e.g. `DateDateFilterLookup` becomes `DateFilterLookup`).

```python
@strawberry_django.filter_type(models.Project)
class ProjectFilter:
    due_date: strawberry_django.DateFilterLookup | None
```
