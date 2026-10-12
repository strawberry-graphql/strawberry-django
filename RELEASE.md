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

Connections over a `distinct()` queryset (e.g. filtered through a many-to-many relation
with `DISTINCT: true`) now count each row once in `totalCount`, using a
`COUNT(DISTINCT pk)` subquery instead of a window count, which would include the rows
duplicated by the join. This fixes inflated totals of nested connections and of top-level
`DjangoListConnection`s selecting `edges`. Nested totals are also read from the
prefetched rows, so they no longer run one `COUNT(*)` query per parent either.

Nested `DjangoCursorConnection`s paginated with `after` or `before` now report the total
count of the whole connection, as top-level ones do, instead of counting only the rows
past the cursor (or `0` when the page was empty).
