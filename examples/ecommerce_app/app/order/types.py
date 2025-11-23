from __future__ import annotations

from app.product.types import ProductType
from app.user.types import UserType
from strawberry import auto, relay

import strawberry_django

from .models import Cart, CartItem, Order, OrderItem


@strawberry_django.type(Order, name="Order")
class OrderType(relay.Node):
    """GraphQL type for completed orders.
    
    Demonstrates computed total field from model_property.
    """

    user: UserType
    total: auto
    items: list[OrderItemType]


@strawberry_django.type(OrderItem, name="OrderItem")
class OrderItemType(relay.Node):
    """GraphQL type for order line items.
    
    Shows price snapshot at time of purchase and computed total.
    """

    product: ProductType
    quantity: auto
    price: auto
    total: auto


@strawberry_django.type(Cart, name="Cart")
class CartType(relay.Node):
    """GraphQL type for shopping carts.
    
    Demonstrates session-based state management and computed totals.
    """

    total: auto
    items: list[CartItemType]


@strawberry_django.type(CartItem, name="CartItem")
class CartItemType(relay.Node):
    """GraphQL type for cart line items.
    
    Shows computed price and total fields using model_property with
    related field access (product__price).
    """

    product: ProductType
    quantity: auto
    price: auto
    total: auto
