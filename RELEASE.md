---
release type: patch
---

Isolate `perm_context` during queryset optimization so a parent field's `HasRetvalPerm` does not leak into nested relation prefetch querysets (preventing cross-app `ValueError` errors in mutations and node queries, as well as same-app permission misapplication and early `is_safe` marking).
