---
release type: patch
---

Fix the `m2m_changed` signal not being sent when adding objects to a many-to-many relation with `set` in
mutations. The relations are now added through the related manager instead of saving the intermediate rows
directly, including when `through_defaults` are given. Existing relations only have their intermediate row
updated when new `through_defaults` are given for them.
