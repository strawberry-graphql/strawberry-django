---
release type: minor
---

Automatically inject FK fields into `.only()` on user-provided `Prefetch` querysets
when the `only` optimization is enabled.

This prevents N+1 queries caused by Django re-fetching the FK field needed to match
prefetched rows back to parent objects.

The optimizer now correctly resolves reverse relations by `related_name` and restricts
FK injection to `ManyToOneRel`, `OneToOneRel`, and `GenericRelation`.
