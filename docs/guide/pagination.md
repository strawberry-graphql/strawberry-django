---
title: Pagination
---

# Pagination

## Default pagination

An interface for limit/offset pagination can be use for basic pagination needs:

```python title="types.py"
@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto
```

```graphql title="schema.graphql"
query {
  fruits(pagination: { offset: 0, limit: 2 }) {
    name
    color
  }
}
```

There is not default limit defined. All elements are returned if no pagination limit is defined.

## Relay pagination

For more complex scenarios, a cursor pagination would be better. For this,
use the [relay integration](./relay.md) to define those.
