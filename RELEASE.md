---
release type: patch
---

Fix custom order methods that take a `sequence` argument failing with an `AssertionError`
when the legacy `order` argument is given through a variable, and every time they are used
in an `order_type` (through the `ordering` argument). They now receive an empty sequence in
those cases.
