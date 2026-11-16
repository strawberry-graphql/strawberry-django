---
release type: minor
---

Add a `queryset` argument to `strawberry_django.field`, `strawberry_django.connection` and
`strawberry_django.offset_paginated`, to retrieve the objects of a query from a custom queryset
instead of the model's default manager:

```python
@strawberry.type
class Query:
    available_fruits: list[Fruit] = strawberry_django.field(
        queryset=models.Fruit.objects.filter(available=True),
    )
    available_fruits_connection: DjangoListConnection[Fruit] = (
        strawberry_django.connection(
            queryset=models.Fruit.objects.filter(available=True),
        )
    )
```

The type's `get_queryset`, permissions, filters, ordering, pagination and the optimizer are applied on
top of it, and a copy of it is used for each request. Fields of model types and fields with a resolver
can't define a `queryset`.
