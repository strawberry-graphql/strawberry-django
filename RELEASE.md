---
release type: patch
---

Fix prefetching inherited and child-owned relations on model-utils inheritance querysets, including when an optimized queryset is cloned. Preserve existing annotations when Strawberry Django adds optimizer annotations to those querysets.
