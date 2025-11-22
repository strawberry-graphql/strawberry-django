from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

import strawberry
from app.base.types import Info
from app.product.models import Product
from strawberry import relay

import strawberry_django
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from strawberry_django.optimizer import optimize
from strawberry_django.permissions import IsAuthenticated, IsStaff

from .models import Cart, CartItem, Order
from .types import CartItemType, CartType, OrderType


@strawberry.type
class Query:
    orders_conn: strawberry_django.relay.DjangoListConnection[OrderType] = (
        strawberry_django.connection(extensions=[IsStaff()])
    )

    @strawberry_django.connection(
        strawberry_django.relay.DjangoListConnection[OrderType],
        extensions=[IsAuthenticated()],
    )
    def my_orders(self, info: Info) -> Iterable[Order]:
        user = info.context.get_user(required=True)
        return Order.objects.filter(user=user)

    @strawberry_django.field
    def my_cart(self, info: Info) -> CartType | None:
        cart_pk = info.context.request.session.get("cart_pk", None)
        if cart_pk is None:
            return None

        cart = optimize(Cart.objects.all(), info).get(pk=cart_pk)
        if cart.status == Cart.Status.FINISHED:
            return None

        return cast("CartType", cart)


@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def cart_add_item(
        self,
        info: Info,
        product: strawberry_django.NodeInput,
        quantity: int = 1,
    ) -> CartItemType:
        if quantity <= 0:
            raise ValidationError({
                "quantity": _("Quantity needs to be equal or greater than 1")
            })

        cart_pk = info.context.request.session.get("cart_pk", None)
        if cart_pk is not None:
            cart = Cart.objects.filter(pk=cart_pk, status=Cart.Status.PENDING).first()
        else:
            cart = None

        if cart is None:
            cart = Cart.objects.create()
            transaction.on_commit(
                lambda: info.context.request.session.update({"cart_pk": cart.pk})
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

        cart_pk = info.context.request.session.get("cart_pk", None)
        if cart_pk is not None:
            cart = Cart.objects.filter(pk=cart_pk, status=Cart.Status.PENDING).first()
        else:
            cart = None

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

        cart_pk = info.context.request.session.get("cart_pk", None)
        if cart_pk is not None:
            cart = Cart.objects.filter(pk=cart_pk, status=Cart.Status.PENDING).first()
        else:
            cart = None

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
        user = info.context.get_user(required=True)

        cart_pk = info.context.request.session.get("cart_pk", None)
        if cart_pk is not None:
            cart = Cart.objects.filter(pk=cart_pk, status=Cart.Status.PENDING).first()
        else:
            cart = None

        if cart is None:
            raise ValidationError(_("You don't have a cart to checkout"))

        if not cart.items.exists():
            raise ValidationError(_("Can't checkout an empty cart"))

        return cast("OrderType", cart.checkout(user))
