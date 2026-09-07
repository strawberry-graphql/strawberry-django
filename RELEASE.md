---
release type: minor
---

Adjust the optimizer to handle when the same field is selected multiple times via aliases with different arguments and the field doesn't have a custom resolver.

Also add support for aliasing custom fields with `annotate`/`prefetch_related` optimizer hint callables, together with three new public helpers (see the [optimizer guide](https://strawberry-graphql.github.io/strawberry-django/guide/optimizer/) for examples):

- `optimizer_hint_key(info)`: a unique, deterministic attribute name for the current field selection (based on the alias), stable between the hint callable and the resolver.
- `get_hint_value(source, info, default_attr=None, *, default=...)`: reads the value produced by an optimizer hint for the current selection.
- `get_field_arguments(info)`: resolves the coerced argument values (including variables and schema defaults) of the current field selection, for use inside hint callables.

Note: inside an optimizer hint callable (and any `get_queryset` reached through the optimizer's prefetch path), `info.path.key` now reports the selection's response key — the alias when the field is aliased — rather than always the field name. This is what makes the per-alias hints deterministic, but code that keys cache or permission logic on `info.path` inside a hint callable should account for it.
