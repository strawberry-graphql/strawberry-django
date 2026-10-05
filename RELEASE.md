---
release type: patch
---

Fix the optimizer ignoring fragments on connection edge types when a node is exposed through both a
`DjangoCursorConnection` and a `DjangoListConnection` (N+1). The optimizer now takes the edge type from the
connection's `edges` field instead of guessing it from the node name.
