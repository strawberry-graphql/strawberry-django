from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry

import strawberry_django

if TYPE_CHECKING:
    from .types import ProductType


@strawberry.type
class Query:
    """Product-related queries demonstrating different query patterns."""

    product: ProductType = strawberry_django.node(
        description="Fetch a single product by its global ID (Relay Node pattern)."
    )

    products: list[ProductType] = strawberry_django.field(
        pagination=True,
        description="List products with offset-based pagination, filtering, and ordering.",
    )

    products_conn: strawberry_django.relay.DjangoListConnection[ProductType] = (
        strawberry_django.connection(
            description="List products with cursor-based Relay connection pagination."
        )
    )


@strawberry.type
class Mutation:
    """Product-related mutations (placeholder for future extensions)."""
