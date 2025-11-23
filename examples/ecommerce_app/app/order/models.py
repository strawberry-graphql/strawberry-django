from __future__ import annotations

import decimal
from typing import TYPE_CHECKING

import strawberry
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django_choices_field.fields import TextChoicesField

from strawberry_django.descriptors import model_property

if TYPE_CHECKING:
    from app.user.models import User
    from django.db.models.manager import RelatedManager


class Order(models.Model):
    """Completed order created from a checked-out cart.

    Demonstrates:
    - One-to-one relationship with Cart
    - Computed total using @model_property with prefetch_related
    - Type hints for related managers (items: RelatedManager[OrderItem])
    """

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    items: RelatedManager[OrderItem]

    user_id: int
    user = models.ForeignKey(
        "user.User",
        verbose_name=_("Customer"),
        on_delete=models.RESTRICT,
        related_name="+",
        db_index=True,
    )
    cart_id: int
    cart = models.OneToOneField(
        "Cart",
        verbose_name=_("Cart"),
        on_delete=models.RESTRICT,
        related_name="+",
        db_index=True,
    )

    @model_property(prefetch_related=["items"])
    def total(self) -> decimal.Decimal:
        return sum((item.total for item in self.items.all()), start=decimal.Decimal(0))


class OrderItem(models.Model):
    """Individual product within an order with quantity and price snapshot.

    Demonstrates:
    - Composite unique constraint (order + product)
    - Price snapshot (stores price at time of purchase)
    - Computed field (total) with optimization hints
    """

    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        unique_together = [  # noqa: RUF012
            ("order", "product"),
        ]

    order_id: int
    order = models.ForeignKey(
        Order,
        verbose_name=_("Order"),
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    product_id: int
    product = models.ForeignKey(
        "product.Product",
        verbose_name=_("Product"),
        on_delete=models.RESTRICT,
        related_name="+",
        db_index=True,
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
        default=1,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    price = models.DecimalField(
        verbose_name=_("Price"),
        max_digits=24,
        decimal_places=2,
    )

    @model_property(only=["quantity", "price"])
    def total(self) -> decimal.Decimal:
        """Calculate line item total (quantity × price).

        The only parameter tells the optimizer to fetch quantity and price
        when this property is accessed, preventing deferred attribute errors.
        """
        return self.quantity * self.price


class Cart(models.Model):
    """Shopping cart for collecting items before checkout.

    Demonstrates:
    - Session-based cart (stored in session, not tied to user)
    - Status enum with TextChoices
    - Business logic method (checkout) with transaction handling
    """

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    @strawberry.enum(name="CartStatus")
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        FINISHED = "finished", _("Finished")

    items: RelatedManager[CartItem]

    status = TextChoicesField(
        verbose_name=_("Status"),
        choices_enum=Status,
        default=Status.PENDING,
    )

    @model_property(prefetch_related=["items"])
    def total(self) -> decimal.Decimal:
        return sum((item.total for item in self.items.all()), start=decimal.Decimal(0))

    @transaction.atomic
    def checkout(self, user: User) -> Order:
        """Convert cart to an order and snapshot product prices.

        Creates an Order and OrderItems from the cart, snapshotting current
        prices at checkout time. Marks the cart as finished.

        Args:
            user: The user placing the order

        Returns:
            The created Order instance

        Note: This method is wrapped in @transaction.atomic to ensure
        atomicity - either all operations succeed or none do.

        """
        order = Order.objects.create(user=user, cart=self)
        for item in self.items.all():
            order.items.create(
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )

        self.status = self.Status.FINISHED
        self.save()

        return order


class CartItem(models.Model):
    """Individual product within a cart with quantity.

    Demonstrates:
    - Composite unique constraint (cart + product)
    - Computed properties using related data (price from product)
    - select_related optimization for foreign key access
    """

    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")
        unique_together = [  # noqa: RUF012
            ("cart", "product"),
        ]

    cart_id: int
    cart = models.ForeignKey(
        Cart,
        verbose_name=_("Cart"),
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    product_id: int
    product = models.ForeignKey(
        "product.Product",
        verbose_name=_("Product"),
        on_delete=models.RESTRICT,
        related_name="+",
        db_index=True,
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
        default=1,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    @model_property(only=["product__price"], select_related=["product"])
    def price(self) -> decimal.Decimal:
        """Get the current price from the related product.

        The only parameter with __ notation (product__price) tells the optimizer
        to fetch the price field from the related product model.
        select_related ensures the product is loaded efficiently with a JOIN.
        """
        return self.product.price

    @model_property(only=["quantity", "product__price"], select_related=["product"])
    def total(self) -> decimal.Decimal:
        """Calculate line item total (quantity × current price).

        Demonstrates accessing related model fields through __notation
        and combining multiple optimization parameters.
        """
        return self.quantity * self.price
