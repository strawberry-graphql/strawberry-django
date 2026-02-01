---
release type: minor
---

Add native federation support via `strawberry_django.federation` module.

New decorators that combine `strawberry_django` functionality with Apollo Federation:

- `strawberry_django.federation.type` - Federation-aware Django type with auto-generated `resolve_reference`
- `strawberry_django.federation.interface` - Federation-aware Django interface
- `strawberry_django.federation.field` - Federation-aware Django field with directives like `@external`, `@requires`, `@provides`

Example usage:

```python
import strawberry
import strawberry_django
from strawberry.federation import Schema

@strawberry_django.federation.type(models.Product, keys=["upc"])
class Product:
    upc: strawberry.auto
    name: strawberry.auto
    price: strawberry.auto
    # resolve_reference is automatically generated!

schema = Schema(query=Query)
```

The auto-generated `resolve_reference` methods support composite keys and multiple keys, and integrate with the query optimizer.
