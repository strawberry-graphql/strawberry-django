---
release type: patch
---

Fix prefetching inherited and child-owned relations on model-utils inheritance querysets, including filtered prefetches across multiple inheritance levels, generic prefetches, `iterator()`, `aiterator()`, and cloned optimized querysets. Preserve existing annotations when Strawberry Django adds optimizer annotations to those querysets.
