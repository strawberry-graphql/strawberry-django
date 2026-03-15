---
release type: patch
---

Fix `FieldExtension` arguments being silently lost on `StrawberryDjangoField`.

When a `FieldExtension` appended arguments to `field.arguments` in its `apply()` method, the arguments worked with `strawberry.field` but silently disappeared with `strawberry_django.field`. This was because the mixin chain (Pagination → Ordering → Filters → Base) created a new list on every `.arguments` access, so `.append()` mutated a temporary copy.

Added a caching `arguments` property to `StrawberryDjangoField` so that the first access computes and caches the full arguments list, and subsequent accesses (including `.append()` from extensions) operate on the same cached list.
