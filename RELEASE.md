---
release type: minor
---

Adjust the optimizer to handle when the same field is selected multiple times via aliases with different arguments and the field doesn't have a custom resolver.

Also add support for aliasing custom fields with `annotate`/`prefetch_related` optimizer hint callables, together with three new public helpers:

- `optimizer_hint_key(info)`: returns a unique, deterministic attribute name for the current field selection (based on the response key, i.e. the alias). It returns the same value inside an optimizer hint callable and inside the field's resolver, so it can be used to name a `Prefetch(to_attr=...)` in the hint and read the value back in the resolver.
- `get_hint_value(source, info, default_attr=None, *, default=...)`: reads the value produced by an optimizer hint for the current selection, checking the alias-scoped attribute/label first and falling back to `default_attr`/`default`. Dict-form annotations with multiple callable labels are supported, so a resolver can combine several per-alias annotated values.
- `get_field_arguments(info)`: resolves the argument values of the current field selection (including variables), usable both inside hint callables and resolvers.

Example:

```python
@strawberry_django.type(Milestone)
class MilestoneType:
    @strawberry_django.field(
        annotate=lambda info: Count(
            "issue",
            filter=Q(issue__name__contains=get_field_arguments(info)["nameContains"]),
        ),
    )
    def issues_count_filtered(self, root, info, name_contains: str) -> int:
        return get_hint_value(root, info, "issues_count_filtered")
```

```graphql
{
  milestoneList {
    foo: issuesCountFiltered(nameContains: "foo")
    bar: issuesCountFiltered(nameContains: "bar")
  }
}
```

Each alias resolves the hint callable with its own scoped `info`, and callable annotations are stored under an alias-scoped label so they don't clash with each other.
