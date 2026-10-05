---
release type: patch
---

Fix a regression from 0.92.0: in async execution, prefetched list fields went through Django's `QuerySet.__aiter__`, which hops to a thread even for cached results. This could split DataLoader batches of child resolvers into extra queries.
