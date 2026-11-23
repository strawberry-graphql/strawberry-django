---
release type: minor
---

Allow namespacing queries and mutations in plain Strawberry types. Django fields and mutations in those types
now default to `UNSET`, so the type can be returned without giving them any values, and fields without a value
are resolved from the model's default manager, like they are in the `Query` type.

```python
@strawberry.type
class FruitQuery:
    fruits: list[Fruit] = strawberry_django.field()
    fruits_connection: DjangoListConnection[Fruit] = strawberry_django.connection()


@strawberry.type
class FruitMutation:
    create_fruit: Fruit = strawberry_django.mutations.create(FruitInput)


@strawberry.type
class Query:
    @strawberry.field
    def fruits(self) -> FruitQuery:
        return FruitQuery()


@strawberry.type
class Mutation:
    @strawberry.field
    def fruits(self) -> FruitMutation:
        return FruitMutation()
```
