from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry
from django_choices_field.fields import TextChoicesField

from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class Brand(models.Model):
    """Product brand model."""

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
    )

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Product model."""

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    @strawberry.enum(name="ProductKind")
    class Kind(models.TextChoices):
        PHYSICAL = "physical", _("Physical")
        VIRTUAL = "virtual", _("Virtual")

    images: RelatedManager[ProductImage]

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
    )
    kind = TextChoicesField(
        verbose_name=_("Category"),
        choices_enum=Kind,
        default=Kind.PHYSICAL,
    )
    brand_id: int | None
    brand = models.ForeignKey(
        Brand,
        verbose_name=_("Brand"),
        on_delete=models.SET_NULL,
        related_name="products",
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )
    description = models.TextField(
        verbose_name=_("Description"),
        default="",
    )
    price = models.DecimalField(
        verbose_name=_("Price"),
        max_digits=24,
        decimal_places=2,
    )

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    """Product image model."""

    class Meta:
        verbose_name = _("Image")
        verbose_name_plural = _("Images")

    product_id: int
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.CASCADE,
        related_name="images",
        db_index=True,
    )
    image = models.ImageField(
        verbose_name=_("Image"),
        max_length=2000,
    )
