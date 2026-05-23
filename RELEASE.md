---
release type: minor
---

`DateFilterLookup`, `TimeFilterLookup` and `DatetimeFilterLookup` no longer require a type parameter, matching `StrFilterLookup`. The generated GraphQL input names also lose their type prefix (e.g. `DateDateFilterLookup` becomes `DateFilterLookup`).

```python
@strawberry_django.filter_type(models.Project)
class ProjectFilter:
    due_date: strawberry_django.DateFilterLookup | None
```

Migrating:

- Drop the type argument from `StrFilterLookup[str]`, `DateFilterLookup[datetime.date]`, etc. The bare lookup now works; the bracket form still resolves to the same class but emits a `DeprecationWarning`.
- `DatetimeFilterLookup.date` and `.time` now accept `Date` / `Time` values (previously typed as `Int`, which never matched Django's `__date` / `__time` transforms).
- `TimeFilterLookup.date` and `.time` were removed. Django's `__date` / `__time` transforms don't apply to `TimeField`.
