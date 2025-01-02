from django.db import models
from tree_queries.fields import TreeNodeForeignKey
from tree_queries.models import TreeNode


class TreeNodeAuthor(TreeNode):
    name = models.CharField(max_length=100)
    parent = TreeNodeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )


class TreeNodeBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(
        TreeNodeAuthor,
        on_delete=models.CASCADE,
        related_name="books",
    )
