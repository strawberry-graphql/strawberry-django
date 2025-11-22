from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ImageField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from strawberry_django.descriptors import model_property


class User(AbstractUser):
    """Default user in the app."""

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    avatar = ImageField(
        verbose_name=_("Avatar"),
        max_length=2000,
        default=None,
        blank=True,
        null=True,
    )
    birth_date = models.DateField(
        verbose_name=_("Birth Date"),
        blank=True,
        null=True,
    )

    @model_property(only=["birth_date"])
    def age(self) -> int | None:
        if self.birth_date is None:
            return None

        days = timezone.now().date() - self.birth_date
        return days // timedelta(days=365)


class Email(models.Model):
    """Email model for users."""

    class Meta:
        verbose_name = _("Email")
        verbose_name_plural = _("Emails")

    user = models.ForeignKey(
        User,
        verbose_name=_("User"),
        related_name="emails",
        on_delete=models.CASCADE,
    )
    email = models.EmailField(
        verbose_name=_("Email"),
        unique=True,
        blank=False,
        null=False,
    )
    is_primary = models.BooleanField(
        verbose_name=_("Is Primary"),
        default=False,
        blank=False,
        null=False,
    )
