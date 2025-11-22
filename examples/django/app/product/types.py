from __future__ import annotations

from strawberry import UNSET, auto, relay

import strawberry_django

from .models import Brand, Product, ProductImage


@strawberry_django.filter_type(Brand, lookups=True)
class BrandFilter:
    name: auto


@strawberry_django.type(
    Brand,
    name="Brand",
    filters=BrandFilter,
)
class BrandType(relay.Node):
    name: auto
    products: list[ProductType]


@strawberry_django.filter_type(Product, lookups=True)
class ProductFilter:
    name: auto
    kind: auto
    brand: BrandFilter | None = UNSET


@strawberry_django.order_type(Product)
class ProductOrdering:
    name: auto
    kind: auto


@strawberry_django.type(
    Product,
    name="Product",
    filters=ProductFilter,
    order=ProductOrdering,
)
class ProductType(relay.Node):
    name: auto
    brand: BrandType | None
    kind: auto
    description: auto
    price: auto
    images: list[ProductImageType]


@strawberry_django.type(ProductImage, name="ProductImage")
class ProductImageType(relay.Node):
    @strawberry_django.field(only=["image"])
    def image(self, root: ProductImage) -> str | None:
        return root.image.url if root.image else None
