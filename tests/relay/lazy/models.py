from django.db import models


class RelayAuthor(models.Model):
    name = models.CharField(max_length=100)


class RelayBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(
        RelayAuthor,
        on_delete=models.CASCADE,
        related_name="books",
    )
