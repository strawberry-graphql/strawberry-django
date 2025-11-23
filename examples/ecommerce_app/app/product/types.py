from __future__ import annotations

from strawberry import UNSET, auto, relay

import strawberry_django

from .models import Brand, Product, ProductImage


@strawberry_django.filter_type(Brand, lookups=True)
class BrandFilter:
    """Filter type for Brand queries with lookup support."""

    name: auto


@strawberry_django.type(
    Brand,
    name="Brand",
    filters=BrandFilter,
)
class BrandType(relay.Node):
    """GraphQL type for Brand model.

    Demonstrates reverse relationship (products) from ForeignKey.
    """

    name: auto
    products: list[ProductType]


@strawberry_django.filter_type(Product, lookups=True)
class ProductFilter:
    """Filter type for Product queries.

    Demonstrates nested filtering with the brand field, allowing queries like:
    filters: { brand: { name: { iContains: "apple" } } }
    """

    name: auto
    kind: auto
    brand: BrandFilter | None = UNSET


@strawberry_django.order_type(Product)
class ProductOrdering:
    """Ordering type for Product queries."""

    name: auto
    kind: auto


@strawberry_django.type(
    Product,
    name="Product",
    filters=ProductFilter,
    order=ProductOrdering,
)
class ProductType(relay.Node):
    """GraphQL type for Product model.

    Demonstrates:
    - Relay Node interface
    - Optional foreign key relationship (brand)
    - Enum field (kind)
    - Related objects list (images)
    - Custom computed fields
    """

    name: auto
    brand: BrandType | None
    kind: auto
    description: auto
    price: auto
    images: list[ProductImageType]

    @strawberry_django.field(only=["price"])
    def formatted_price(self, root: Product) -> str:
        """Return price formatted as currency string.

        Demonstrates a simple computed field for display formatting.
        """
        return f"${root.price:.2f}"


@strawberry_django.type(ProductImage, name="ProductImage")
class ProductImageType(relay.Node):
    """GraphQL type for ProductImage model."""

    @strawberry_django.field(only=["image"])
    def image(self, root: ProductImage) -> str | None:
        """Return the image URL if available."""
        return root.image.url if root.image else None


@strawberry_django.input(Product)
class ProductInput:
    """Input type for creating products."""

    name: auto
    brand: relay.GlobalID | None = None
    kind: auto
    description: auto
    price: auto


@strawberry_django.input(Brand)
class BrandInput:
    """Input type for creating brands."""

    name: auto
