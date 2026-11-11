---
release type: minor
---

Add a `lookup_key` argument to `strawberry_django.field`, to retrieve single objects by a model field other than
the primary key. The argument is named after the field, and its type is resolved from the model field. Without
`lookup_key`, the argument is still `pk: ID!`.

```python
@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field()
    fruit_by_slug: Fruit | None = strawberry_django.field(lookup_key="slug")
    # Typed as the model's primary key, e.g. `UUID` for a `UUIDField`
    order: Order = strawberry_django.field(lookup_key="pk")
```

```graphql
type Query {
  fruit(pk: ID!): Fruit!
  fruitBySlug(slug: String!): Fruit
  order(pk: UUID!): Order!
}
```
