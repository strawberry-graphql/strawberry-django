---
release type: patch
---

Fix `DuplicatedTypeName` errors when using `FilterLookup[str]` by:

- Exporting `StrFilterLookup` from the top-level `strawberry_django` module
- Adding a deprecation warning when using `FilterLookup[str]` or `FilterLookup[uuid.UUID]`
- Updating documentation to recommend using specific lookup types

Users should migrate from:
```python
from strawberry_django import FilterLookup

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    name: FilterLookup[str] | None
```

To:
```python
from strawberry_django import StrFilterLookup

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    name: StrFilterLookup | None
```
