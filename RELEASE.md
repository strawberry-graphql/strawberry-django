---
release type: minor
---

Adjust the optimizer to handle when the same field is selected multiple times via aliases with different arguments and the field doesn't have a custom resolver.

Also add support for aliasing custom fields with `annotate`/`prefetch_related` optimizer hint callables, together with three new public helpers (see the [optimizer guide](https://strawberry-graphql.github.io/strawberry-django/guide/optimizer/) for examples):

- `optimizer_hint_key(info)`: a unique, deterministic attribute name for the current field selection (based on the alias), stable between the hint callable and the resolver.
- `get_hint_value(source, info, default_attr=None, *, default=...)`: reads the value produced by an optimizer hint for the current selection.
- `get_field_arguments(info)`: resolves the argument values of the current field selection (including variables), usable in both hint callables and resolvers.
