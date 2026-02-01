---
title: Federation
---

# Federation

Strawberry Django works seamlessly with
[Strawberry's Federation support](https://strawberry.rocks/docs/guides/federation).
You can use either Strawberry's federation decorators directly or the Django-specific
`strawberry_django.federation` module which provides auto-generated `resolve_reference`
methods.

## Using `strawberry_django.federation` (Recommended)

The `strawberry_django.federation` module provides Django-aware federation decorators
that automatically generate `resolve_reference` methods for your entity types:

```python
import strawberry
import strawberry_django
from strawberry.federation import Schema as FederationSchema

from . import models


@strawberry_django.federation.type(models.Product, keys=["upc"])
class Product:
    upc: strawberry.auto
    name: strawberry.auto
    price: strawberry.auto
    # resolve_reference is automatically generated!


@strawberry_django.federation.type(models.Review, keys=["id"])
class Review:
    id: strawberry.auto
    body: strawberry.auto
    product: Product


@strawberry.type
class Query:
    @strawberry_django.field
    def products(self) -> list[Product]:
        return models.Product.objects.all()


schema = FederationSchema(query=Query)
```

### Federation Parameters

The `@strawberry_django.federation.type` decorator accepts all standard
`@strawberry_django.type` parameters plus federation-specific ones:

| Parameter         | Type              | Description                                                               |
| ----------------- | ----------------- | ------------------------------------------------------------------------- |
| `keys`            | `list[str]`       | Key fields for entity resolution (e.g., `["id"]` or `["sku", "package"]`) |
| `extend`          | `bool`            | Whether this type extends a type from another subgraph                    |
| `shareable`       | `bool`            | Whether this type can be resolved by multiple subgraphs                   |
| `inaccessible`    | `bool`            | Whether this type is hidden from the public API                           |
| `authenticated`   | `bool`            | Whether this type requires authentication                                 |
| `policy`          | `list[list[str]]` | Access policy for this type                                               |
| `requires_scopes` | `list[list[str]]` | Required OAuth scopes for this type                                       |
| `tags`            | `list[str]`       | Metadata tags for this type                                               |

### Multiple Keys

You can define multiple key fields:

```python
@strawberry_django.federation.type(models.Product, keys=["id", "upc"])
class Product:
    id: strawberry.auto
    upc: strawberry.auto
    name: strawberry.auto
```

### Composite Keys

For composite keys (multiple fields that together form a key), use a space-separated
string:

```python
@strawberry_django.federation.type(models.ProductVariant, keys=["sku package"])
class ProductVariant:
    sku: strawberry.auto
    package: strawberry.auto
    price: strawberry.auto
```

### Custom `resolve_reference`

If you need custom logic, you can still define your own `resolve_reference`:

```python
from strawberry.types.info import Info


@strawberry_django.federation.type(models.Product, keys=["upc"])
class Product:
    upc: strawberry.auto
    name: strawberry.auto

    @classmethod
    def resolve_reference(cls, upc: str, info: Info) -> "Product":
        # Custom implementation with select_related
        return models.Product.objects.select_related("category").get(upc=upc)
```

### Federation Fields

Use `strawberry_django.federation.field` for federation-specific field directives:

```python
@strawberry_django.federation.type(models.Product, keys=["id"])
class Product:
    id: strawberry.auto
    name: strawberry.auto = strawberry_django.federation.field(external=True)
    price: strawberry.auto = strawberry_django.federation.field(shareable=True)
    display_name: str = strawberry_django.federation.field(requires=["name"])
```

Field parameters:

| Parameter         | Type              | Description                                      |
| ----------------- | ----------------- | ------------------------------------------------ |
| `authenticated`   | `bool`            | Whether this field requires authentication       |
| `external`        | `bool`            | Field is defined in another subgraph             |
| `requires`        | `list[str]`       | Fields required from other subgraphs             |
| `provides`        | `list[str]`       | Fields this resolver provides to other subgraphs |
| `override`        | `str`             | Override field from another subgraph             |
| `policy`          | `list[list[str]]` | Access policy for this field                     |
| `requires_scopes` | `list[list[str]]` | Required OAuth scopes for this field             |
| `shareable`       | `bool`            | Field can be resolved by multiple subgraphs      |
| `tags`            | `list[str]`       | Metadata tags for this field                     |
| `inaccessible`    | `bool`            | Field is hidden from the public API              |

### Interfaces

Federation interfaces are also supported:

```python
@strawberry_django.federation.interface(models.Product, keys=["id"])
class ProductInterface:
    id: strawberry.auto
    name: strawberry.auto
```

## Using Strawberry's Federation Directly

You can also use Strawberry's federation decorators alongside `strawberry_django`:

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

    @classmethod
    def resolve_reference(cls, upc: str) -> "Product":
        return models.Product.objects.get(upc=upc)
```

## Creating a Federated Schema

Use `strawberry.federation.Schema` instead of the regular `strawberry.Schema`:

```python
from strawberry.federation import Schema


@strawberry.type
class Query:
    @strawberry_django.field
    def products(self) -> list[Product]:
        return models.Product.objects.all()


schema = Schema(query=Query)
```

## Django-Specific Considerations

### Query Optimizer

The [Query Optimizer](../guide/optimizer.md) works with federated schemas. Add the
extension as usual:

```python
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension],
)
```

The auto-generated `resolve_reference` methods integrate with the query optimizer
when using `strawberry_django.federation`.

### Authentication

When using federation with Django authentication, ensure your gateway forwards
authentication headers. See [Authentication](../guide/authentication.md) for
configuring authentication in your Django service.

## Further Reading

For complete federation documentation, see:

- [Strawberry Federation Guide](https://strawberry.rocks/docs/guides/federation)
- [Federation Specification](https://www.apollographql.com/docs/federation/)
