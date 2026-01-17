

0.74.0 - 2026-01-17
-------------------

Add configurable `PAGINATION_MAX_LIMIT` setting to cap pagination requests, preventing clients from requesting unlimited data via `limit: null` or excessive limits.

This addresses security and performance concerns by allowing projects to enforce a maximum number of records that can be requested through pagination.

**Configuration:**

```python
STRAWBERRY_DJANGO = {
    "PAGINATION_MAX_LIMIT": 1000,  # Cap all requests to 1000 records
}
```

When set, any client request with `limit: null`, negative limits, or limits exceeding the configured maximum will be capped to `PAGINATION_MAX_LIMIT`. Defaults to `None` (unlimited) for backward compatibility, though setting a limit is recommended for production environments.

Works with both offset-based and window-based pagination.

This release was contributed by @bellini666 in https://github.com/strawberry-graphql/strawberry-django/pull/847
