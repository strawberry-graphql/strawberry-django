---
release type: minor
---

**Breaking change**: `PAGINATION_MAX_LIMIT` now defaults to `100` instead of `None`, so clients can
no longer request more than 100 rows in a single page by default.

Previously, the cap was off and `PAGINATION_DEFAULT_LIMIT` only applied when the client omitted the
limit, which let any client send `limit: 9999999` and receive the full table in one response.

To restore the old behavior, set `PAGINATION_MAX_LIMIT` to `None` in `STRAWBERRY_DJANGO`
(not recommended for production).
