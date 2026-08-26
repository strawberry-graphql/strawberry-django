---
release type: patch
---

Fix the query optimizer dropping a manually applied `select_related` from the
`only()` mask when another field on the same model shares its name as a
prefix without a `__` boundary (e.g. `company` vs `company_branch`). This
previously made Django raise `FieldError: cannot be both deferred and
traversed using select_related at the same time` whenever only the longer
sibling was selected in the query.
