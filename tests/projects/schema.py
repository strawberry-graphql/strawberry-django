import asyncio
from typing import Iterable, List, Optional, Type, cast

import strawberry
import strawberry.django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db.models import Exists, OuterRef, Prefetch
from django.db.models.query import QuerySet
from strawberry import relay
from strawberry.types.info import Info
from typing_extensions import Annotated

from strawberry_django.fields.types import ListInput, NodeInput, NodeInputPartial
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import (
    Assignee,
    Favorite,
    FavoriteQuerySet,
    Issue,
    Milestone,
    Project,
    Quiz,
    Tag,
)

UserModel = cast(Type[AbstractUser], get_user_model())


@strawberry.django.type(UserModel)
class UserType(relay.Node):
    username: relay.NodeID[str]
    email: strawberry.auto
    is_active: strawberry.auto
    is_superuser: strawberry.auto
    is_staff: strawberry.auto

    @strawberry.django.field(only=["first_name", "last_name"])
    def full_name(self, root: AbstractUser) -> str:
        return f"{root.first_name or ''} {root.last_name or ''}".strip()


@strawberry.django.type(UserModel)
class StaffType(relay.Node):
    username: relay.NodeID[str]
    email: strawberry.auto
    is_active: strawberry.auto
    is_superuser: strawberry.auto
    is_staff: strawberry.auto

    @classmethod
    def get_queryset(
        cls,
        queryset: QuerySet[AbstractUser],
        info: Info,
    ) -> QuerySet[AbstractUser]:
        return queryset.filter(is_staff=True)


@strawberry.django.type(Project)
class ProjectType(relay.Node):
    name: strawberry.auto
    due_date: strawberry.auto
    milestones: List["MilestoneType"]
    cost: strawberry.auto


@strawberry.django.filter(Milestone, lookups=True)
class MilestoneFilter:
    name: strawberry.auto
    project: strawberry.auto
    search: Optional[str]

    def filter_search(self, queryset: QuerySet[Milestone]):
        return queryset.filter(name__contains=self.search)


@strawberry.django.order(Project)
class ProjectOrder:
    id: strawberry.auto
    name: strawberry.auto


@strawberry.django.order(Milestone)
class MilestoneOrder:
    name: strawberry.auto
    project: Optional[ProjectOrder]


@strawberry.django.type(Milestone, filters=MilestoneFilter, order=MilestoneOrder)
class MilestoneType(relay.Node):
    name: strawberry.auto
    due_date: strawberry.auto
    project: ProjectType
    issues: List["IssueType"]

    @strawberry.django.field(
        prefetch_related=[
            lambda info: Prefetch(
                "issues",
                queryset=Issue.objects.filter(
                    Exists(
                        Assignee.objects.filter(
                            issue=OuterRef("pk"),
                            user_id=info.context.request.user.id,
                        ),
                    ),
                ),
                to_attr="_my_issues",
            ),
        ],
    )
    def my_issues(self) -> List["IssueType"]:
        return self._my_issues  # type: ignore

    @strawberry.django.field
    async def async_field(self, value: str) -> str:
        await asyncio.sleep(0)
        return f"value: {value}"


@strawberry.django.type(Favorite)
class FavoriteType(relay.Node):
    name: strawberry.auto
    user: UserType
    issue: "IssueType"

    @classmethod
    def get_queryset(cls, queryset: FavoriteQuerySet, info: Info) -> QuerySet:
        return queryset.by_user(info.context.request.user)


@strawberry.django.type(Issue)
class IssueType(relay.Node):
    name: strawberry.auto
    milestone: MilestoneType
    priority: strawberry.auto
    kind: strawberry.auto
    name_with_priority: strawberry.auto
    name_with_kind: str = strawberry.django.field(only=["kind", "name"])
    tags: List["TagType"]
    issue_assignees: List["AssigneeType"]
    favorite_set: ListConnectionWithTotalCount["FavoriteType"] = (
        strawberry.django.connection()
    )


@strawberry.django.type(Tag)
class TagType(relay.Node):
    name: strawberry.auto
    issues: ListConnectionWithTotalCount[IssueType] = strawberry.django.connection()


@strawberry.django.type(Quiz)
class QuizType(relay.Node):
    title: strawberry.auto
    sequence: strawberry.auto


@strawberry.django.partial(Tag)
class TagInputPartial(NodeInputPartial):
    name: strawberry.auto


@strawberry.django.input(Issue)
class IssueInput:
    name: strawberry.auto
    milestone: "MilestoneInputPartial"
    priority: strawberry.auto
    kind: strawberry.auto
    tags: Optional[List[NodeInput]]


@strawberry.django.type(Assignee)
class AssigneeType(relay.Node):
    user: UserType
    owner: strawberry.auto


@strawberry.django.partial(Assignee)
class IssueAssigneeInputPartial(NodeInputPartial):
    user: strawberry.auto
    owner: strawberry.auto


@strawberry.input
class AssigneeThroughInputPartial:
    owner: Optional[bool] = strawberry.UNSET


@strawberry.django.partial(UserModel)
class AssigneeInputPartial(NodeInputPartial):
    through_defaults: Optional[AssigneeThroughInputPartial] = strawberry.UNSET


@strawberry.django.partial(Issue)
class IssueInputPartial(NodeInput, IssueInput):
    tags: Optional[ListInput[TagInputPartial]]
    assignees: Optional[ListInput[AssigneeInputPartial]]
    issue_assignees: Optional[ListInput[IssueAssigneeInputPartial]]


@strawberry.django.input(Issue)
class MilestoneIssueInput:
    name: strawberry.auto


@strawberry.django.partial(Project)
class ProjectInputPartial(NodeInputPartial):
    name: strawberry.auto
    milestones: Optional[List["MilestoneInputPartial"]]


@strawberry.django.input(Milestone)
class MilestoneInput:
    name: strawberry.auto
    project: ProjectInputPartial
    issues: Optional[List[MilestoneIssueInput]]


@strawberry.django.partial(Milestone)
class MilestoneInputPartial(NodeInputPartial):
    name: strawberry.auto


@strawberry.type
class Query:
    """All available queries for this schema."""

    node: Optional[relay.Node] = strawberry.django.node()

    favorite: Optional[FavoriteType] = strawberry.django.node()
    issue: Optional[IssueType] = strawberry.django.node(description="Foobar")
    milestone: Optional[
        Annotated["MilestoneType", strawberry.lazy("tests.projects.schema")]
    ] = strawberry.django.node()
    milestone_mandatory: MilestoneType = strawberry.django.node()
    milestones: List[MilestoneType] = strawberry.django.node()
    project: Optional[ProjectType] = strawberry.django.node()
    tag: Optional[TagType] = strawberry.django.node()
    staff: Optional[StaffType] = strawberry.django.node()
    staff_list: List[Optional[StaffType]] = strawberry.django.node()

    issue_list: List[IssueType] = strawberry.django.field()
    milestone_list: List[MilestoneType] = strawberry.django.field(
        order=MilestoneOrder,
        filters=MilestoneFilter,
        pagination=True,
    )
    project_list: List[ProjectType] = strawberry.django.field()
    tag_list: List[TagType] = strawberry.django.field()

    favorite_conn: ListConnectionWithTotalCount[FavoriteType] = (
        strawberry.django.connection()
    )
    issue_conn: ListConnectionWithTotalCount[
        strawberry.LazyType[
            "IssueType",
            "tests.projects.schema",  # type: ignore  # noqa: F821
        ]
    ] = strawberry.django.connection()
    milestone_conn: ListConnectionWithTotalCount[MilestoneType] = (
        strawberry.django.connection()
    )

    project_conn: ListConnectionWithTotalCount[ProjectType] = (
        strawberry.django.connection()
    )
    tag_conn: ListConnectionWithTotalCount[TagType] = strawberry.django.connection()
    staff_conn: ListConnectionWithTotalCount[StaffType] = strawberry.django.connection()

    @strawberry.django.field
    def me(self, info: Info) -> Optional[UserType]:
        user = info.context.request.user
        if not user.is_authenticated:
            return None

        return cast(UserType, user)

    @strawberry.django.connection(ListConnectionWithTotalCount[ProjectType])
    def project_conn_with_resolver(self, root: str, name: str) -> Iterable[Project]:
        return Project.objects.filter(name__contains=name)


schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
