---
release type: patch
---

Fix offset pagination extensions so they receive pagination, order, and filter
arguments consistently with connection fields. This allows extensions to inspect
filters for permission/validation while keeping resolvers tolerant of missing
params.
