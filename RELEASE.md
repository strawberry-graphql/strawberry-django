---
release type: patch
---

Fix the debug toolbar middleware crashing with `TypeError: list indices must be integers or slices, not str` when batching is enabled. A batched response is a JSON array, and the middleware now adds the `debugToolbar` data to each result in it.
