---
release type: patch
---

Optimize nested connections that select only `totalCount`.

Previously, a nested connection with no `edges { node }` selection was not prefetched,
so `totalCount` ran one `COUNT(*)` query per parent:

```graphql
query {
  milestones {
    edges {
      node {
        issues {
          totalCount
        }
      }
    }
  }
}
```

The optimizer now prefetches such connections too, fetching only the first row of each
parent, which carries the window total count. The query above now runs 2 queries instead
of 1 + N.

Nested connections over a `distinct()` queryset (e.g. filtered through a many-to-many
relation with `DISTINCT: true`) now count each row once in `totalCount`, using a
`COUNT(DISTINCT pk)` subquery per parent instead of a window count, which would include
the rows duplicated by the join. This total is also read from the prefetched rows, so it
no longer runs one `COUNT(*)` query per parent either.
