---
release type: patch
---

Fix `offset_paginated` fields applying the filter pipeline twice per resolution.

`StrawberryOffsetPaginatedExtension.resolve` forwards `filters`/`order`/`pagination`
to the inner resolver (so extensions and custom resolvers can access them), but then
re-applied them on the queryset the resolver returned. Filters, permission filtering
and the optimizer pass all ran twice; for a filter spanning a multivalued relation
the second `.filter()` duplicated the relation JOINs, which can grow the intermediate
row count quadratically and turn a sub-second query into a multi-minute one.

The queryset returned by the inner resolver is now passed straight to
`resolve_paginated`, matching the behavior of relay connection fields.
