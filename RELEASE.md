---
release type: minor
---

Require Strawberry GraphQL 0.322.2 or newer, which fixes Relay pagination when combining `first` with `before`. Update compatibility tests for the corrected pagination behavior and make schema comparisons independent of top-level definition order.
