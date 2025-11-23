from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ImageField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from strawberry_django.descriptors import model_property


class User(AbstractUser):
    """User model extending Django's AbstractUser.
    
    This model demonstrates:
    - Custom fields (avatar, birth_date)
    - Computed properties with @model_property
    - Type hints for better IDE support
    """

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
        """Calculate user's age from birth_date.
        
        The @model_property decorator with only=["birth_date"] tells the optimizer
        to fetch birth_date when this property is requested, preventing N+1 queries.
        """
        if self.birth_date is None:
            return None

        days = timezone.now().date() - self.birth_date
        return days // timedelta(days=365)


class Email(models.Model):
    """Email addresses associated with users.
    
    Demonstrates a one-to-many relationship where users can have multiple email addresses,
    with one marked as primary for communication.
    """

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
