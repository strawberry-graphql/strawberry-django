---
release type: patch
---

Fix FK `_id` fields (e.g. `color_id: auto`) in input types failing with `mutations.create()`. Previously, `prepare_create_update()` didn't recognize FK attnames, causing the value to be silently dropped and `full_clean()` to fail. Now attname fields are mapped and their raw PK values are passed through directly.
