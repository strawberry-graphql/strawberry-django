import asyncio
import datetime
import decimal
from typing import Iterable, List, Optional, Type, cast, Union

import strawberry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Prefetch,
    Q,
)
from django.db.models.functions import Now
from django.db.models.query import QuerySet
from strawberry import relay
from strawberry.types.info import Info
from typing_extensions import Annotated

import strawberry_django
from strawberry_django import mutations
from strawberry_django.auth.queries import get_current_user
from strawberry_django.fields.types import ListInput, NodeInput, NodeInputPartial
from strawberry_django.mutations import resolvers
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.permissions import (
    HasPerm,
    HasRetvalPerm,
    IsAuthenticated,
    IsStaff,
    IsSuperuser,
)
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


@strawberry_django.type(UserModel)
class UserType(relay.Node):
    username: relay.NodeID[str]
    email: strawberry.auto
    is_active: strawberry.auto
    is_superuser: strawberry.auto
    is_staff: strawberry.auto

    @strawberry_django.field(only=["first_name", "last_name"])
    def full_name(self, root: AbstractUser) -> str:
        return f"{root.first_name or ''} {root.last_name or ''}".strip()


@strawberry_django.type(UserModel)
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
        **kwargs,
    ) -> QuerySet[AbstractUser]:
        return queryset.filter(is_staff=True)


@strawberry_django.filter(Project, lookups=True)
class ProjectFilter:
    name: strawberry.auto
    due_date: strawberry.auto


@strawberry_django.type(Project, filters=ProjectFilter)
class ProjectType(relay.Node):
    name: strawberry.auto
    due_date: strawberry.auto
    milestones: List["MilestoneType"]
    milestones_count: int = strawberry_django.field(annotate=Count("milestone"))
    is_delayed: bool = strawberry_django.field(
        annotate=ExpressionWrapper(
            Q(due_date__lt=Now()),
            output_field=BooleanField(),
        ),
    )
    cost: strawberry.auto = strawberry_django.field(extensions=[IsAuthenticated()])
    is_small: strawberry.auto

    next_milestones_property: strawberry.auto

    @strawberry_django.field(
        prefetch_related=lambda _: Prefetch(
            "milestones",
            to_attr="next_milestones_pf",
            queryset=Milestone.objects.filter(due_date__isnull=False).order_by("due_date")
        )
    )
    def next_milestones(self) -> "list[MilestoneType]":
        """
        The milestones for the project ordered by their due date
        """
        if hasattr(self, 'next_milestones_pf'):
            return self.next_milestones_pf
        else:
            return self.milestones.filter(due_date__isnull=False).order_by("due_date")


@strawberry_django.filter(Milestone, lookups=True)
class MilestoneFilter:
    name: strawberry.auto
    project: strawberry.auto
    search: Optional[str]

    def filter_search(self, queryset: QuerySet[Milestone]):
        return queryset.filter(name__contains=self.search)


@strawberry_django.order(Project)
class ProjectOrder:
    id: strawberry.auto
    name: strawberry.auto


@strawberry_django.order(Milestone)
class MilestoneOrder:
    name: strawberry.auto
    project: Optional[ProjectOrder]


@strawberry_django.type(Milestone, filters=MilestoneFilter, order=MilestoneOrder)
class MilestoneType(relay.Node):
    name: strawberry.auto
    due_date: strawberry.auto
    project: ProjectType
    issues: List["IssueType"]

    @strawberry_django.field(
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

    @strawberry_django.field(
        annotate={
            "_my_bugs_count": lambda info: Count(
                "issue",
                filter=Q(
                    issue__issue_assignee__user_id=info.context.request.user.id,
                    issue__kind=Issue.Kind.BUG,
                ),
            ),
        },
    )
    def my_bugs_count(self, root: Milestone) -> int:
        return root._my_bugs_count  # type: ignore

    @strawberry_django.field
    async def async_field(self, value: str) -> str:
        await asyncio.sleep(0)
        return f"value: {value}"


@strawberry_django.type(Favorite)
class FavoriteType(relay.Node):
    name: strawberry.auto
    user: UserType
    issue: "IssueType"

    @classmethod
    def get_queryset(cls, queryset: FavoriteQuerySet, info: Info, **kwargs) -> QuerySet:
        return queryset.by_user(info.context.request.user)


@strawberry_django.type(Issue)
class IssueType(relay.Node):
    name: strawberry.auto
    milestone: MilestoneType
    priority: strawberry.auto
    kind: strawberry.auto
    name_with_priority: strawberry.auto
    name_with_kind: str = strawberry_django.field(only=["kind", "name"])
    tags: List["TagType"]
    issue_assignees: List["AssigneeType"]
    favorite_set: ListConnectionWithTotalCount["FavoriteType"] = (
        strawberry_django.connection()
    )

    @strawberry_django.field(select_related="milestone", only="milestone__name")
    def milestone_name(self) -> str:
        return self.milestone.name

    @strawberry_django.field(select_related="milestone")
    def milestone_name_without_only_optimization(self) -> str:
        return self.milestone.name


@strawberry_django.type(Tag)
class TagType(relay.Node):
    name: strawberry.auto
    issues: ListConnectionWithTotalCount[IssueType] = strawberry_django.connection()


@strawberry_django.type(Quiz)
class QuizType(relay.Node):
    title: strawberry.auto
    sequence: strawberry.auto


@strawberry_django.partial(Tag)
class TagInputPartial(NodeInputPartial):
    name: strawberry.auto


@strawberry_django.input(Issue)
class IssueInput:
    name: strawberry.auto
    milestone: "MilestoneInputPartial"
    priority: strawberry.auto
    kind: strawberry.auto
    tags: Optional[List[NodeInput]]


@strawberry_django.type(Assignee)
class AssigneeType(relay.Node):
    user: UserType
    owner: strawberry.auto


@strawberry_django.partial(Assignee)
class IssueAssigneeInputPartial(NodeInputPartial):
    user: Optional[NodeInputPartial]
    owner: strawberry.auto


@strawberry.input
class AssigneeThroughInputPartial:
    owner: Optional[bool] = strawberry.UNSET


@strawberry_django.partial(UserModel)
class AssigneeInputPartial(NodeInputPartial):
    through_defaults: Optional[AssigneeThroughInputPartial] = strawberry.UNSET


@strawberry_django.partial(Issue)
class IssueInputPartial(NodeInput, IssueInput):
    tags: Optional[ListInput[TagInputPartial]]  # type: ignore
    assignees: Optional[ListInput[AssigneeInputPartial]]
    issue_assignees: Optional[ListInput[IssueAssigneeInputPartial]]


@strawberry_django.partial(Issue)
class IssueInputPartialWithoutId(IssueInput):
    tags: Optional[ListInput[TagInputPartial]]  # type: ignore
    assignees: Optional[ListInput[AssigneeInputPartial]]
    issue_assignees: Optional[ListInput[IssueAssigneeInputPartial]]


@strawberry_django.input(Issue)
class MilestoneIssueInput:
    name: strawberry.auto


@strawberry_django.partial(Project)
class ProjectInputPartial(NodeInputPartial):
    name: strawberry.auto
    milestones: Optional[List["MilestoneInputPartial"]]


@strawberry_django.input(Milestone)
class MilestoneInput:
    name: strawberry.auto
    project: ProjectInputPartial
    issues: Optional[List[MilestoneIssueInput]]


@strawberry_django.partial(Milestone)
class MilestoneInputPartial(NodeInputPartial):
    name: strawberry.auto


@strawberry.type
class ProjectConnection(ListConnectionWithTotalCount[ProjectType]):
    """Project connection documentation."""


ProjectFeedItem = Annotated[Union[IssueType, MilestoneType], strawberry.union('ProjectFeedItem')]


@strawberry.type
class ProjectFeedConnection(relay.Connection[ProjectFeedItem]):
    pass


@strawberry.type
class Query:
    """All available queries for this schema."""

    node: Optional[relay.Node] = strawberry_django.node()

    favorite: Optional[FavoriteType] = strawberry_django.node()
    issue: Optional[IssueType] = strawberry_django.node(description="Foobar")
    milestone: Optional[
        Annotated["MilestoneType", strawberry.lazy("tests.projects.schema")]
    ] = strawberry_django.node()
    milestone_mandatory: MilestoneType = strawberry_django.node()
    milestones: List[MilestoneType] = strawberry_django.node()
    project: Optional[ProjectType] = strawberry_django.node()
    project_login_required: Optional[ProjectType] = strawberry_django.node(
        extensions=[IsAuthenticated()],
    )
    tag: Optional[TagType] = strawberry_django.node()
    staff: Optional[StaffType] = strawberry_django.node()
    staff_list: List[Optional[StaffType]] = strawberry_django.node()

    issue_list: List[IssueType] = strawberry_django.field()
    milestone_list: List[MilestoneType] = strawberry_django.field(
        order=MilestoneOrder,
        filters=MilestoneFilter,
        pagination=True,
    )
    project_list: List[ProjectType] = strawberry_django.field()
    tag_list: List[TagType] = strawberry_django.field()

    favorite_conn: ListConnectionWithTotalCount[FavoriteType] = (
        strawberry_django.connection()
    )
    issue_conn: ListConnectionWithTotalCount[
        strawberry.LazyType[
            "IssueType",
            "tests.projects.schema",  # type: ignore  # noqa: F821
        ]
    ] = strawberry_django.connection()
    milestone_conn: ListConnectionWithTotalCount[MilestoneType] = (
        strawberry_django.connection()
    )

    project_conn: ProjectConnection = strawberry_django.connection()
    tag_conn: ListConnectionWithTotalCount[TagType] = strawberry_django.connection()
    staff_conn: ListConnectionWithTotalCount[StaffType] = strawberry_django.connection()

    # Login required to resolve
    issue_login_required: IssueType = strawberry_django.node(
        extensions=[IsAuthenticated()],
    )
    issue_login_required_optional: Optional[IssueType] = strawberry_django.node(
        extensions=[IsAuthenticated()],
    )
    # Staff required to resolve
    issue_staff_required: IssueType = strawberry_django.node(extensions=[IsStaff()])
    issue_staff_required_optional: Optional[IssueType] = strawberry_django.node(
        extensions=[IsStaff()],
    )
    # Superuser required to resolve
    issue_superuser_required: IssueType = strawberry_django.node(
        extensions=[IsSuperuser()],
    )
    issue_superuser_required_optional: Optional[IssueType] = strawberry_django.node(
        extensions=[IsSuperuser()],
    )
    # User permission on "projects.view_issue" to resolve
    issue_perm_required: IssueType = strawberry_django.node(
        extensions=[HasPerm(perms=["projects.view_issue"])],
    )
    issue_perm_required_optional: Optional[IssueType] = strawberry_django.node(
        extensions=[HasPerm(perms=["projects.view_issue"])],
    )
    issue_list_perm_required: List[IssueType] = strawberry_django.field(
        extensions=[HasPerm(perms=["projects.view_issue"])],
    )
    issue_conn_perm_required: ListConnectionWithTotalCount[IssueType] = (
        strawberry_django.connection(
            extensions=[HasPerm(perms=["projects.view_issue"])],
        )
    )
    # User permission on the resolved object for "projects.view_issue"
    issue_obj_perm_required: IssueType = strawberry_django.node(
        extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
    )
    issue_obj_perm_required_optional: Optional[IssueType] = strawberry_django.node(
        extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
    )
    issue_list_obj_perm_required: List[IssueType] = strawberry_django.field(
        extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
    )
    issue_conn_obj_perm_required: ListConnectionWithTotalCount[IssueType] = (
        strawberry_django.connection(
            extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
        )
    )

    @strawberry_django.field(
        extensions=[HasPerm(perms=["projects.view_issue"], with_superuser=True)]
    )
    async def async_user_resolve(self) -> bool:
        return True

    @strawberry_django.field
    def me(self, info: Info) -> Optional[UserType]:
        user = get_current_user(info, strict=True)
        if not user.is_authenticated:
            return None

        return cast(UserType, user)

    @strawberry_django.connection(ProjectConnection)
    def project_conn_with_resolver(self, root: str, name: str) -> Iterable[Project]:
        return Project.objects.filter(name__contains=name)


@strawberry.type
class Mutation:
    """All available mutations for this schema."""

    create_issue: IssueType = mutations.create(
        IssueInput,
        handle_django_errors=True,
        argument_name="input",
    )
    update_issue: IssueType = mutations.update(
        IssueInputPartial,
        handle_django_errors=True,
        argument_name="input",
    )
    update_issue_with_key_attr: IssueType = mutations.update(
        IssueInputPartialWithoutId,
        handle_django_errors=True,
        argument_name="input",
        key_attr="name",
    )
    delete_issue: IssueType = mutations.delete(
        NodeInput,
        handle_django_errors=True,
        argument_name="input",
    )
    delete_issue_with_key_attr: IssueType = mutations.delete(
        MilestoneIssueInput,
        handle_django_errors=True,
        argument_name="input",
        key_attr="name",
    )
    update_project: ProjectType = mutations.update(
        ProjectInputPartial,
        handle_django_errors=True,
        argument_name="input",
    )
    create_milestone: MilestoneType = mutations.create(
        MilestoneInput,
        handle_django_errors=True,
        argument_name="input",
    )

    @mutations.input_mutation(handle_django_errors=True)
    def create_project(
        self,
        info: Info,
        name: str,
        cost: Annotated[
            decimal.Decimal,
            strawberry.argument(description="The project's cost"),
        ],
        due_date: Optional[datetime.datetime] = None,
    ) -> ProjectType:
        """Create project documentation."""
        if cost > 500:
            # Field error without error code:
            raise ValidationError({"cost": "Cost cannot be higher than 500"})
        if cost < 0:
            # Field error with error code:
            raise ValidationError(
                {
                    "cost": ValidationError(
                        "Cost cannot be lower than zero",
                        code="min_cost",
                    ),
                },
            )
        project = Project(
            name=name,
            cost=cost,
            due_date=due_date,
        )
        project.full_clean()
        project.save()

        return cast(
            ProjectType,
            project,
        )

    @mutations.input_mutation(handle_django_errors=True)
    def create_quiz(
        self,
        info: Info,
        title: str,
        full_clean_options: bool = False,
    ) -> QuizType:
        return cast(
            QuizType,
            resolvers.create(
                info,
                Quiz,
                {"title": title},
                full_clean={"exclude": ["sequence"]} if full_clean_options else True,
                key_attr="id",
            ),
        )


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
