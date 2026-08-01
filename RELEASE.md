---
release type: patch
---

Fix an N+1 on `totalCount` of nested connections optimized by prefetching:
parents whose prefetched first-page partition came back empty issued one
`COUNT(*)` query each, even though an empty first page already proves the
total count is 0.
