---
release type: patch
---

`@strawberry_django.type` types no longer overwrite `is_type_of` methods in superclasses.
Instead, the superclass' result will be taken into account as well.
