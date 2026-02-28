---
release type: patch
---

Fix N+1 queries when using `optimize()` inside a `Prefetch` object with `.only()` optimization. The optimizer now correctly auto-adds the FK field needed by Django to match prefetched objects back to their parent.
