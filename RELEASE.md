---
release type: minor
---

`BoolFilterLookup`, `IDFilterLookup`, `IntFilterLookup`, `FloatFilterLookup` and
`DecimalFilterLookup` no longer require a type parameter, matching
`StrFilterLookup`/`DateFilterLookup`/`TimeFilterLookup`/`DatetimeFilterLookup`
(#891, #910). This completes the same fix for every remaining entry in
`type_filter_map` that was still generic.

```python
@strawberry_django.filter_type(models.Project)
class ProjectFilter:
    is_active: strawberry_django.BoolFilterLookup | None
    id: strawberry_django.IDFilterLookup | None
    priority: strawberry_django.IntFilterLookup | None
    weight: strawberry_django.FloatFilterLookup | None
    budget: strawberry_django.DecimalFilterLookup | None
```

Migrating:

- Drop the type argument from `BaseFilterLookup[bool]`, `ComparisonFilterLookup[int]`,
  etc. when referencing the now-concrete classes directly. The bare lookup now works;
  the bracket form still resolves to the same class but emits a `DeprecationWarning`.
- Generated GraphQL input names lose their type prefix, e.g. `IntComparisonFilterLookup`
  becomes `IntFilterLookup`, `BoolBaseFilterLookup` becomes `BoolFilterLookup`, and
  `IDBaseFilterLookup` becomes `IDFilterLookup`. Clients referencing these inputs by
  name need to update.

Building on many models with many filterable fields previously re-specialized these
generic lookups independently at every usage site, which is a meaningful share of
schema build time for large schemas (see #519). Making them concrete removes that
redundant generic re-specialization for the most common filter field types.
