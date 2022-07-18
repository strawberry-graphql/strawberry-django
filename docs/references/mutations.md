# Mutations
Mutations are used to create, update or delete objects in GraphQL

In the `types.py` create Input fields for the classes that are going to be used for mutations. Note that `partial=True` should be for foreign keys fields so that their fields are not set to required by default.

```python
# types.py
from strawberry import auto

@strawberry.django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    color: 'Color'

@strawberry.django.type(models.Color)
class Color:
    id: auto
    name: auto
    
@strawberry.django.input(models.Color, partial=True)
class ColorInput:
    id: auto
    name: auto
    
@strawberry.django.input(models.Fruit)
class FruitInput:
    id: auto
    name: auto
    color: 'ColorInput'    

```

For the schema.py mutations can be defined as follows:

```python
# schema.py
from strawberry.django import mutations

@strawberry.type
class Mutation:
    createColor: Color =  mutations.create(ColorInput)

    createFruit: Fruit = mutations.create(FruitInput)
    createFruits: List[Fruit] = mutations.create(FruitInput)
    updateFruits: List[Fruit] = mutations.update(FruitPartialInput)
    deleteFruits: List[Fruit] = mutations.delete()

schema = strawberry.Schema(mutation=Mutation)
```

Mutations for creating Color and Fruit can be written as follows:

```graphql

mutation newColor ($name:String!) {
  createColor(data: {name: $name}) {
    id
    name
  }
}


mutation newFruit ($name:String!, $colorid: id!) {
  createFruit(data: {name: $name, color{ id: $colorid }) {
    id
    name
    color {
      name
      id
    }
  }
}
```

## Filtering

Filters can be added to update and delete mutations. More information in the [filtering](filters.md) section.

```python
# schema.py
from strawberry.django import mutations

@strawberry.type
class Mutation:
    updateFruits: List[Fruit] = mutations.update(FruitPartialInput, filters=FruitFilter)
    deleteFruits: List[Fruit] = mutations.delete(filters=FruitFilter)

schema = strawberry.Schema(mutation=Mutation)
```
