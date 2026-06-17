---
release type: patch
---

Resolving a Relay node's `id` no longer goes through `sync_to_async` on every call.
`resolve_id`/`resolve_id_attr` now read the primary key directly off the in-memory
instance, removing an unnecessary thread hop (and contextvars copy) in async contexts.
The deferred-field fallback still bridges database access safely.
