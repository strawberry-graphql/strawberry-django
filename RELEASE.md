---
release type: patch
---

Fix `DjangoOptimizerExtension` not optimizing querysets when executing subscription events, which caused N+1
queries for the same types that were optimized in queries and mutations.
