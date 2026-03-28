---
release type: patch
---

Fix `FieldError` when using the optimizer with `django-polymorphic` models.

The optimizer now uses the CamelCase model name for polymorphic optimization hints (e.g., `ArtProject___field` instead of `app_label__artproject___field`). This ensures that `django-polymorphic` correctly handles mismatched optimization hints during the realization of mixed querysets by raising an `AssertionError` (which it catches) instead of an unhandled `FieldError`. This change also avoids potential name collisions with lowercase reverse relations in multi-table inheritance.

A `polymorphic` optional dependency extra has been added, which sets the lower limit version to `4.0.0`. Install with `pip install strawberry-graphql-django[polymorphic]` to pull in `django-polymorphic`.
