from django.db import models
from tree_queries.fields import TreeNodeForeignKey
from tree_queries.models import TreeNode


class MPTTAuthor(TreeNode):
    name = models.CharField(max_length=100)
    parent = TreeNodeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )


class MPTTBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(
        MPTTAuthor,
        on_delete=models.CASCADE,
        related_name="books",
    )
