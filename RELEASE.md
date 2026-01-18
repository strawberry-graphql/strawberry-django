---
release type: patch
---

Pagination `pageInfo.limit` now returns the actual limit applied (after defaults and max caps), not the raw request value.

For example, with `PAGINATION_DEFAULT_LIMIT=20`, `PAGINATION_MAX_LIMIT=50`:

```graphql
{ fruits(pagination: { limit: null }) { pageInfo { limit } } }
```

Before:
```json
{
  "data": {
    "fruits": {
      "pageInfo": {
        "limit": null
      }
    }
  }
}
```

After:
```json
{
  "data": {
    "fruits": {
      "pageInfo": {
        "limit": 20
      }
    }
  }
}
```

Also fixes `limit: null` to use `PAGINATION_DEFAULT_LIMIT` instead of `PAGINATION_MAX_LIMIT`.
