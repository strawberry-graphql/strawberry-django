from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

import strawberry
from app.base.types import Info
from app.product.models import Product
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from strawberry import relay

import strawberry_django
from strawberry_django.optimizer import optimize
from strawberry_django.permissions import IsAuthenticated, IsStaff

from .models import Cart, CartItem, Order
from .types import CartItemType, CartType, OrderType


def get_current_cart(info: Info) -> Cart | None:
    """Get the current cart from session, handling stale/invalid cart_pk.

    This helper demonstrates:
    - Session-based cart storage (allows anonymous users to shop)
    - Graceful handling of stale/deleted carts with first() instead of get()
    - Query optimization with the optimizer's optimize() function

    Args:
        info: The GraphQL resolve info containing request context

    Returns:
        The current pending cart or None if no valid cart exists

    """
    cart_pk = info.context.request.session.get("cart_pk")
    if cart_pk is None:
        return None

    # Use first() instead of get() to handle stale/deleted carts gracefully
    return (
        optimize(Cart.objects.all(), info)
        .filter(
            pk=cart_pk,
            status=Cart.Status.PENDING,
        )
        .first()
    )


@strawberry.type
class Query:
    """Order and cart-related queries."""

    orders_conn: strawberry_django.relay.DjangoListConnection[OrderType] = (
        strawberry_django.connection(extensions=[IsStaff()])
    )
    """List all orders (staff only). Demonstrates permission extensions."""

    @strawberry_django.connection(
        strawberry_django.relay.DjangoListConnection[OrderType],
        extensions=[IsAuthenticated()],
    )
    def my_orders(self, info: Info) -> Iterable[Order]:
        """Get the current user's orders.

        Demonstrates:
        - Authentication requirement with IsAuthenticated() extension
        - Filtering queryset based on current user
        - Relay connection pattern
        """
        user = info.context.get_user(required=True)
        return Order.objects.filter(user=user)

    @strawberry_django.field
    def my_cart(self, info: Info) -> CartType | None:
        """Get the current session's shopping cart.

        Works for both authenticated and anonymous users via session storage.
        Returns null if no cart exists.
        """
        cart = get_current_cart(info)
        return cast("CartType | None", cart)


@strawberry.type
class Mutation:
    """Cart and order-related mutations."""

    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def cart_add_item(
        self,
        info: Info,
        product: strawberry_django.NodeInput,
        quantity: int = 1,
    ) -> CartItemType:
        """Add a product to the cart or increment its quantity.

        Demonstrates:
        - NodeInput for accepting global IDs
        - Automatic error handling with handle_django_errors
        - Transaction safety with @transaction.atomic
        - Session updates using transaction.on_commit
        - Get-or-create pattern for cart items

        Args:
            product: Global ID of the product to add
            quantity: Number of items to add (default: 1)

        Returns:
            The created or updated cart item

        Raises:
            ValidationError: If quantity is less than 1

        """
        if quantity <= 0:
            raise ValidationError({
                "quantity": _("Quantity needs to be equal or greater than 1")
            })

        cart = get_current_cart(info)
        if cart is None:
            cart = Cart.objects.create()
            # Use on_commit to ensure cart_pk is saved before updating session
            transaction.on_commit(
                lambda pk=cart.pk: info.context.request.session.update({"cart_pk": pk})
            )

        product_obj = product.id.resolve_node_sync(info, ensure_type=Product)
        try:
            cart_item = cart.items.get(product=product_obj)
        except CartItem.DoesNotExist:
            cart_item = cart.items.create(
                product=product_obj,
                quantity=quantity,
            )
        else:
            cart_item.quantity += quantity
            cart_item.save()

        return cast("CartItemType", cart_item)

    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def cart_update_item(
        self,
        info: Info,
        item: relay.GlobalID,
        quantity: int,
    ) -> CartItemType:
        if quantity <= 0:
            raise ValidationError({
                "quantity": _("Quantity needs to be equal or greater than 1")
            })

        cart_item = item.resolve_node_sync(info, ensure_type=CartItem)
        cart = get_current_cart(info)

        if cart is None or cart_item.cart != cart:
            raise PermissionDenied(_("You are not authorized to change this cart item"))

        cart_item.quantity = quantity
        cart_item.save()

        return cast("CartItemType", cart_item)

    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def cart_remove_item(
        self,
        info: Info,
        item: relay.GlobalID,
    ) -> CartItemType:
        cart_item = item.resolve_node_sync(info, ensure_type=CartItem)
        cart = get_current_cart(info)

        if cart is None or cart_item.cart != cart:
            raise PermissionDenied(_("You are not authorized to change this cart item"))

        # Save pk to return the removed object after as django will set it to None
        pk = cart_item.pk
        cart_item.delete()
        cart_item.pk = pk

        return cast("CartItemType", cart_item)

    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def cart_checkout(self, info: Info) -> OrderType:
        """Convert the current cart into an order.

        Demonstrates:
        - Authentication requirement (get_user with required=True)
        - Business logic encapsulation (cart.checkout method)
        - Session cleanup with transaction.on_commit
        - Validation before processing

        Returns:
            The created order

        Raises:
            PermissionDenied: If user is not authenticated
            ValidationError: If cart is empty or doesn't exist

        """
        user = info.context.get_user(required=True)
        cart = get_current_cart(info)

        if cart is None:
            raise ValidationError(_("You don't have a cart to checkout"))

        if not cart.items.exists():
            raise ValidationError(_("Can't checkout an empty cart"))

        order = cart.checkout(user)
        # Clear cart from session after successful checkout
        transaction.on_commit(lambda: info.context.request.session.pop("cart_pk", None))
        return cast("OrderType", order)
