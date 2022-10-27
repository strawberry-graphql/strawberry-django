# Pagination

Currently only offset and limit type of pagination are supported.

```python
@strawberry.django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto
```

```graphql
query {
  fruits(pagination: { offset: 0, limit: 2 }) {
    name
    color
  }
}
# -> fruits: [{ name: "strawberry", color: "red" }, { name: "banana", color: "yellow" }]
```

There is not default limit defined. All elements are returned if no pagination limit is defined.
