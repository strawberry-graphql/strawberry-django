---
title: Queries
---

# Queries

Queries can be written using `strawberry_django.field()` to load the fields defined in the `types.py` file.

```python
#schema.py

import strawberry
import strawberry_django

from .types import Fruit

@strawberry.type
class Query:

    fruit: Fruit = strawberry_django.field()
    fruits: list[Fruit] = strawberry_django.field()

schema = strawberry.Schema(query=Query)
```

> ![TIP]
> You must name your query class "Query" or decorate it with `@strawberry.type(name="Query")` for the single query default primary filter to work

For the single queries (like `Fruit` above), Strawberry comes with a default primary key search filter in the GraphiQL interface. The query `Fruits` gets all the objects in the Fruits by default. To query specific sets of objects a filter need to be added in the `types.py` file.
