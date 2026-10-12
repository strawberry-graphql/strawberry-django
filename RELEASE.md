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

The optimizer now prefetches such connections, and nested `OffsetPaginated` fields that
select only `totalCount`, too, fetching only the first row of each parent, which carries
the window total count. The query above now runs 2 queries instead of 1 + N.

Nested connections and `OffsetPaginated` fields also keep the first row of each parent
when its page is empty (e.g. an offset or cursor past its end, or `first: 0`), so their
`totalCount` no longer runs one `COUNT(*)` query per parent either.

This also fixes `totalCount` in these cases:

- Connections over a `distinct()` queryset (e.g. filtered through a many-to-many
  relation with `DISTINCT: true`) count each row once, instead of also counting the rows
  duplicated by the join. Nested ones no longer return duplicated edges either. This
  fixes nested connections and top-level `DjangoListConnection`s selecting `edges`.
- Nested `DjangoCursorConnection`s paginated with `after` or `before` report the total
  count of the whole connection, as top-level ones do, instead of counting only the rows
  past the cursor. This doesn't apply yet when `first` and `last` are combined.
- Nested many-to-many connections and `OffsetPaginated` fields with an empty page no
  longer count each row once per related object.
