---
release type: minor
---

Propagate child-type `only=` hints through method resolvers that declare the
relation via `select_related` / `prefetch_related`. Previously they were
silently dropped, causing deferred loads or `KeyError`s on descriptors
without a deferred-load fallback (e.g. `djmoney.MoneyField`) once the
parent's `select_related` reached past a single hop.

```python
@strawberry_django.type(Child)
class ChildType:
    @strawberry_django.field(only=["extra_data"])
    def extra(self) -> str:
        return self.extra_data


@strawberry_django.type(Parent)
class ParentType:
    @strawberry_django.field(select_related=["child", "child__site"])
    def child(self) -> ChildType | None:
        return self.child
```

`child.extra_data` is now included in the parent's first SELECT.
