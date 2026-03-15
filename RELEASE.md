---
release type: minor
---

Prefetch callables can now receive resolved field arguments as keyword parameters.

If a `prefetch_related` callable declares parameters beyond `info`, the optimizer
will automatically resolve the field's GraphQL arguments and pass matching ones
as keyword arguments. Existing callables that only accept `info` continue to work
unchanged.

Also adds `strawberry_django.get_field_arguments(info)` — a public utility that
resolves the current field's GraphQL arguments from an `Info` object without
raw AST access.
