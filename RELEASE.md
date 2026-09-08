---
release type: minor
---

Require Strawberry GraphQL 0.322.2 or newer, which fixes Relay pagination when combining `first` with `before`. Update compatibility tests for the corrected pagination behavior and make schema comparisons independent of top-level definition order.

Update GraphQL-core 3.3 compatibility for the 3.3.0rc0 execution API, preserving resolve-info context and adapting fragment and variable values used by the query optimizer.
