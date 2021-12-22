# Mutations

```python
#schema.py
from strawberry_django import mutations

@strawberry.type
class Mutation:
    createFruit: Fruit = mutations.create(FruitInput)
    createFruits: List[Fruit] = mutations.create(FruitInput)
    updateFruits: List[Fruit] = mutations.update(FruitPartialInput)
    deleteFruits: List[Fruit] = mutations.delete()

schema = strawberry.Schema(mutation=Mutation)
```

## Filtering

Filters can be addedd to update and delete mutations. See more information about [filtering](filters.md).

```python
#schema.py

from strawberry_django import mutations

@strawberry.type
class Mutation:
    updateFruits: List[Fruit] = mutations.update(FruitPartialInput, filters=FruitFilter)
    deleteFruits: List[Fruit] = mutations.delete(filters=FruitFilter)

schema = strawberry.Schema(mutation=Mutation)
```
