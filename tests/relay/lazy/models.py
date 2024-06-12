from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel


class RelayAuthor(MPTTModel):
    name = models.CharField(max_length=100)

    parent = TreeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )


class RelayBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(
        RelayAuthor,
        on_delete=models.CASCADE,
        related_name="books",
    )
