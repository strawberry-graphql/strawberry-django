from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry

import strawberry_django

if TYPE_CHECKING:
    from .types import ProductType


@strawberry.type
class Query:
    product: ProductType = strawberry_django.node()
    products: list[ProductType] = strawberry_django.field(pagination=True)
    products_conn: strawberry_django.relay.DjangoListConnection[ProductType] = (
        strawberry_django.connection()
    )


@strawberry.type
class Mutation: ...
