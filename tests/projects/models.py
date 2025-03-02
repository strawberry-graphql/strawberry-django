from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, QuerySet
from django.utils.translation import gettext_lazy as _
from django_choices_field import TextChoicesField

from strawberry_django.descriptors import model_property
from strawberry_django.utils.typing import UserType

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

User = get_user_model()


class NamedModel(models.Model):
    class Meta:
        abstract = True

    name = models.CharField(
        max_length=255,
    )


class Project(NamedModel):
    class Status(models.TextChoices):
        """Project status options."""

        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    milestones: "RelatedManager[Milestone]"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )
    status = TextChoicesField(
        help_text=_("This project's status"),
        choices_enum=Status,
        default=Status.ACTIVE,
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        default=None,
    )
    cost = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )

    @model_property(annotate={"_milestone_count": Count("milestone")})
    def is_small(self) -> bool:
        return self._milestone_count < 3  # type: ignore


class Milestone(NamedModel):
    issues: "RelatedManager[Issue]"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        default=None,
    )
    project_id: int
    project = models.ForeignKey[Project](
        Project,
        on_delete=models.CASCADE,
        related_name="milestones",
        related_query_name="milestone",
    )


class FavoriteQuerySet(QuerySet):
    def by_user(self, user: UserType):
        if user.is_anonymous:
            return self.none()
        return self.filter(user__pk=user.pk)


class Favorite(models.Model):
    """A user's favorite issues."""

    class Meta:
        # Needed to allow type's get_queryset() to access a model's custom QuerySet
        ordering = ("name",)
        base_manager_name = "objects"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )
    name = models.CharField(max_length=32)
    user = models.ForeignKey(
        User,
        related_name="favorite_set",
        on_delete=models.CASCADE,
    )
    issue = models.ForeignKey(
        "Issue",
        related_name="favorite_set",
        on_delete=models.CASCADE,
    )

    objects = FavoriteQuerySet.as_manager()


class Issue(NamedModel):
    class Meta:  # type: ignore
        ordering = ("id",)

    class Kind(models.TextChoices):
        """Issue kind options."""

        BUG = "b", "Bug"
        FEATURE = "f", "Feature"

    comments: "RelatedManager[Issue]"
    issue_assignees: "RelatedManager[Assignee]"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )
    kind = models.CharField(
        verbose_name="kind",
        help_text="the kind of the issue",
        choices=Kind.choices,
        max_length=max(len(k.value) for k in Kind),
        default=None,
        blank=True,
        null=True,
    )
    priority = models.IntegerField(
        default=0,
    )
    milestone_id: Optional[int]
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.SET_NULL,
        related_name="issues",
        related_query_name="issue",
        null=True,
        blank=True,
        default=None,
    )
    tags = models.ManyToManyField["Tag", Any](
        "Tag",
        related_name="issues",
        related_query_name="issue",
    )
    assignees = models.ManyToManyField["User", "Assignee"](
        User,
        through="Assignee",
        related_name="+",
    )

    @property
    def name_with_kind(self) -> str:
        return f"{self.kind}: {self.name}"

    @model_property(only=["kind", "priority"])
    def name_with_priority(self) -> str:
        """Field doc."""
        return f"{self.kind}: {self.priority}"


class Assignee(models.Model):
    class Meta:
        unique_together = [  # noqa: RUF012
            ("issue", "user"),
        ]

    issues: "RelatedManager[Issue]"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )
    issue_id: int
    issue = models.ForeignKey[Issue](
        Issue,
        on_delete=models.CASCADE,
        related_name="issue_assignees",
        related_query_name="issue_assignee",
    )
    user_id: int
    user = models.ForeignKey["User"](
        User,
        on_delete=models.CASCADE,
        related_name="issue_assignees",
        related_query_name="issue_assignee",
    )
    owner = models.BooleanField(
        default=False,
    )


class Tag(NamedModel):
    class Meta:  # type: ignore
        ordering = ("id",)

    issues: "RelatedManager[Issue]"

    id = models.BigAutoField(
        verbose_name="ID",
        primary_key=True,
    )


class Quiz(models.Model):
    title = models.CharField(
        "title",
        max_length=255,
    )
    sequence = models.PositiveIntegerField(
        "sequence",
        default=1,
        unique=True,
    )

    def save(self, *args, **kwargs):
        if self._state.adding:
            max_ = self.__class__.objects.aggregate(max=models.Max("sequence"))["max"]

            if max_ is not None:
                self.sequence = max_ + 1
        super().save(*args, **kwargs)
