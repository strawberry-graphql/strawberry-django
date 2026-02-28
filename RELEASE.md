---
release type: patch
---

Fix N+1 queries when using `optimize()` inside a user-provided `Prefetch` with `only` optimization enabled. The FK field needed by Django to match prefetched rows back to parent objects is now automatically included.
