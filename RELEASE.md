---
release type: patch
---

Fix optimizer skipping optimization entirely for aliased fields. When a GraphQL query uses aliases for the same field (e.g., `a: milestones { id }` and `b: milestones { id }`), the optimizer now merges them into a single prefetch instead of skipping optimization, preventing N+1 queries.
