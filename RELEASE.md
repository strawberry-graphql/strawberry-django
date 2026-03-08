---
release type: patch
---

Fix docs example for `process_filters` custom filter method where `prefix` was missing a trailing `__`, causing Django `FieldError`. Also add a `UserWarning` in `process_filters()` when a non-empty prefix doesn't end with `__` to help users catch this mistake early.
