# Apollo Federation

Strawberry Django works seamlessly with
[Strawberry's Apollo Federation support](https://strawberry.rocks/docs/guides/federation).
Since federation is handled at the Strawberry level, you can use all federation
features directly with your Django types.

## Basic Usage

Use Strawberry's federation decorators alongside `strawberry_django`:

```python
import strawberry
import strawberry_django
from strawberry.federation.schema_directives import Key

from . import models


@strawberry_django.type(models.Product, directives=[Key(fields="upc")])
class Product:
    upc: strawberry.auto
    name: strawberry.auto
    price: strawberry.auto


@strawberry_django.type(models.Review, directives=[Key(fields="id")])
class Review:
    id: strawberry.auto
    body: strawberry.auto
    product: Product
```

## Creating a Federated Schema

Use `strawberry.federation.Schema` instead of the regular `strawberry.Schema`:

```python
import strawberry
from strawberry.federation import Schema


@strawberry.type
class Query:
    @strawberry_django.field
    def products(self) -> list[Product]:
        return models.Product.objects.all()


schema = Schema(query=Query, enable_federation_2=True)
```

## Reference Resolvers

When other services need to resolve your Django entities, define `resolve_reference`:

```python
@strawberry_django.type(models.Product, directives=[Key(fields="upc")])
class Product:
    upc: strawberry.auto
    name: strawberry.auto
    price: strawberry.auto

    @classmethod
    def resolve_reference(cls, upc: str) -> "Product":
        return models.Product.objects.get(upc=upc)
```

## Django-Specific Considerations

### Query Optimizer

The [Query Optimizer](../guide/optimizer.md) works with federated schemas. Add the
extension as usual:

```python
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = Schema(
    query=Query,
    enable_federation_2=True,
    extensions=[DjangoOptimizerExtension],
)
```

### Authentication

When using federation with Django authentication, ensure your gateway forwards
authentication headers. See [Authentication](../guide/authentication.md) for
configuring authentication in your Django service.

## Further Reading

For complete federation documentation, see:

- [Strawberry Federation Guide](https://strawberry.rocks/docs/guides/federation)
- [Apollo Federation Specification](https://www.apollographql.com/docs/federation/)
