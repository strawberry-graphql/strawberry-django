---
release type: patch
---

Fix nullable connections (e.g. when guarded by a permission extension) eagerly
fetching the entire table before the connection applied its pagination. The
return type is now unwrapped from `StrawberryOptional`/other containers so the
queryset evaluation stays deferred and the connection can apply a `LIMIT`.
