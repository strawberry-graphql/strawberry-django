import asyncio
import datetime
import decimal
from collections.abc import Iterable
from typing import Annotated, Optional, cast

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
    Subquery,
    Value,
)
from django.db.models.fields import CharField
from django.db.models.functions import Now
from django.db.models.query import QuerySet
from strawberry import UNSET, relay
from strawberry.types.info import Info

import strawberry_django
from strawberry_django import mutations
from strawberry_django.auth.queries import get_current_user
from strawberry_django.fields.types import ListInput, NodeInput, NodeInputPartial
from strawberry_django.mutations import resolvers
from strawberry_django.optimizer import (
    DjangoOptimizerExtension,
    OptimizerStore,
    optimize,
)
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.permissions import (
    HasPerm,
    HasRetvalPerm,
    IsAuthenticated,
    IsStaff,
    IsSuperuser,
    filter_for_user,
)
from strawberry_django.relay import DjangoListConnection

from .models import (
    Assignee,
    Favorite,
    FavoriteQuerySet,
    Issue,
    Milestone,
    NamedModel,
    Project,
    Quiz,
    Tag,
)

UserModel = get_user_model()


@strawberry_django.interface(NamedModel)
class Named:
    name: strawberry.auto


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


@strawberry_django.filter_type(Project, lookups=True)
class ProjectFilter:
    name: strawberry.auto
    due_date: strawberry.auto


@strawberry_django.type(Project, filters=ProjectFilter, pagination=True)
class ProjectType(relay.Node, Named):
    due_date: strawberry.auto
    is_small: strawberry.auto
    is_delayed: bool = strawberry_django.field(
        annotate=ExpressionWrapper(
            Q(due_date__lt=Now()),
            output_field=BooleanField(),
        ),
    )
    cost: strawberry.auto = strawberry_django.field(extensions=[IsAuthenticated()])
    milestones: list["MilestoneType"] = strawberry_django.field(pagination=True)
    milestones_count: int = strawberry_django.field(annotate=Count("milestone"))
    custom_milestones_model_property: strawberry.auto
    first_milestone: Optional["MilestoneType"] = strawberry_django.field(
        field_name="milestones"
    )
    first_milestone_required: "MilestoneType" = strawberry_django.field(
        field_name="milestones"
    )
    milestone_conn: DjangoListConnection["MilestoneType"] = (
        strawberry_django.connection(field_name="milestones")
    )
    milestones_paginated: OffsetPaginated["MilestoneType"] = (
        strawberry_django.offset_paginated(field_name="milestones")
    )

    @strawberry_django.field(
        prefetch_related=lambda info: Prefetch(
            "milestones",
            queryset=optimize(
                Milestone.objects.all(),
                info,
                store=OptimizerStore.with_hints(only="project_id"),
            ),
            to_attr="custom_milestones",
        )
    )
    @staticmethod
    def custom_milestones(
        parent: strawberry.Parent, info: Info
    ) -> list["MilestoneType"]:
        return parent.custom_milestones


@strawberry_django.filter_type(Milestone, lookups=True)
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


@strawberry_django.filter_type(Issue, lookups=True)
class IssueFilter:
    name: strawberry.auto

    @strawberry_django.filter_field()
    def search(self, value: str, prefix: str) -> Q:
        return Q(name__contains=value)


@strawberry_django.order(Issue)
class IssueOrder:
    name: strawberry.auto


@strawberry_django.type(
    Milestone, filters=MilestoneFilter, order=MilestoneOrder, pagination=True
)
class MilestoneType(relay.Node, Named):
    due_date: strawberry.auto
    project: ProjectType
    issues: list["IssueType"] = strawberry_django.field(
        filters=IssueFilter,
        order=IssueOrder,
        pagination=True,
    )
    first_issue: Optional["IssueType"] = strawberry_django.field(field_name="issues")
    first_issue_required: "IssueType" = strawberry_django.field(field_name="issues")

    graphql_path: str = strawberry_django.field(
        annotate=lambda info: Value(
            ",".join(map(str, info.path.as_list())),
            output_field=CharField(max_length=255),
        )
    )
    mixed_annotated_prefetch: str = strawberry_django.field(
        annotate=lambda info: Value("dummy", output_field=CharField(max_length=255)),
        prefetch_related="issues",
    )
    mixed_prefetch_annotated: str = strawberry_django.field(
        annotate=Value("dummy", output_field=CharField(max_length=255)),
        prefetch_related=lambda info: Prefetch("issues"),
    )
    issues_paginated: OffsetPaginated["IssueType"] = strawberry_django.offset_paginated(
        field_name="issues",
        order=IssueOrder,
    )
    issues_with_filters: DjangoListConnection["IssueType"] = (
        strawberry_django.connection(
            field_name="issues",
            filters=IssueFilter,
        )
    )

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
    def my_issues(self) -> list["IssueType"]:
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
class IssueType(relay.Node, Named):
    milestone: MilestoneType
    priority: strawberry.auto
    kind: strawberry.auto
    name_with_priority: strawberry.auto
    name_with_kind: str = strawberry_django.field(only=["kind", "name"])
    tags: list["TagType"]
    issue_assignees: list["AssigneeType"]
    staff_assignees: list["StaffType"] = strawberry_django.field(field_name="assignees")
    favorite_set: DjangoListConnection["FavoriteType"] = strawberry_django.connection()

    @strawberry_django.field(select_related="milestone", only="milestone__name")
    def milestone_name(self) -> str:
        return self.milestone.name

    @strawberry_django.field(select_related="milestone")
    def milestone_name_without_only_optimization(self) -> str:
        return self.milestone.name

    @strawberry_django.field(
        annotate={
            "_private_name": lambda info: Subquery(
                filter_for_user(
                    Issue.objects.all(),
                    info.context.request.user,
                    ["projects.view_issue"],
                )
                .filter(id=OuterRef("pk"))
                .values("name")[:1],
            ),
        },
    )
    def private_name(self, root: Issue) -> Optional[str]:
        return root._private_name  # type: ignore


@strawberry_django.type(Tag)
class TagType(relay.Node, Named):
    issues: DjangoListConnection[IssueType] = strawberry_django.connection()

    @strawberry_django.field
    def issues_with_selected_related_milestone_and_project(self) -> list[IssueType]:
        # here, the `select_related` is on the queryset directly, and not on the field
        return (
            self.issues.all()  # type: ignore
            .select_related("milestone", "milestone__project")
            .order_by("id")
        )


@strawberry_django.type(Quiz)
class QuizType(relay.Node):
    title: strawberry.auto
    sequence: strawberry.auto

    @classmethod
    def get_queryset(
        cls,
        queryset: QuerySet[Quiz],
        info: Info,
        **kwargs,
    ) -> QuerySet[Quiz]:
        return queryset.order_by("title")


@strawberry_django.partial(Tag)
class TagInputPartial(NodeInputPartial):
    name: strawberry.auto


@strawberry_django.input(Issue)
class IssueInput:
    name: strawberry.auto
    milestone: "MilestoneInputPartial"
    priority: strawberry.auto
    kind: strawberry.auto
    tags: Optional[list[NodeInput]]
    extra: Optional[str] = strawberry.field(default=UNSET, graphql_type=Optional[int])


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
    tags: Optional[ListInput[TagInputPartial]] = UNSET  # type: ignore
    assignees: Optional[ListInput[AssigneeInputPartial]] = UNSET
    issue_assignees: Optional[ListInput[IssueAssigneeInputPartial]] = UNSET


@strawberry_django.partial(Issue)
class IssueInputPartialWithoutId(IssueInput):
    tags: Optional[ListInput[TagInputPartial]] = UNSET  # type: ignore
    assignees: Optional[ListInput[AssigneeInputPartial]] = UNSET
    issue_assignees: Optional[ListInput[IssueAssigneeInputPartial]] = UNSET


@strawberry_django.input(Issue)
class MilestoneIssueInput:
    name: strawberry.auto


@strawberry_django.partial(Issue)
class MilestoneIssueInputPartial:
    name: strawberry.auto
    tags: Optional[list[TagInputPartial]]


@strawberry_django.partial(Project)
class ProjectInputPartial(NodeInputPartial):
    name: strawberry.auto
    milestones: Optional[list["MilestoneInputPartial"]]


@strawberry_django.input(Milestone)
class MilestoneInput:
    name: strawberry.auto
    project: ProjectInputPartial
    issues: Optional[list[MilestoneIssueInput]]


@strawberry_django.partial(Milestone)
class MilestoneInputPartial(NodeInputPartial):
    name: strawberry.auto
    issues: Optional[list[MilestoneIssueInputPartial]]
    project: Optional[ProjectInputPartial]


@strawberry.type
class ProjectConnection(DjangoListConnection[ProjectType]):
    """Project connection documentation."""


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
    milestones: list[MilestoneType] = strawberry_django.node()
    project: Optional[ProjectType] = strawberry_django.node()
    project_mandatory: ProjectType = strawberry_django.node()
    project_login_required: Optional[ProjectType] = strawberry_django.node(
        extensions=[IsAuthenticated()],
    )
    tag: Optional[TagType] = strawberry_django.node()
    staff: Optional[StaffType] = strawberry_django.node()
    staff_list: list[Optional[StaffType]] = strawberry_django.node()

    issue_list: list[IssueType] = strawberry_django.field()
    issues_paginated: OffsetPaginated[IssueType] = strawberry_django.offset_paginated()
    milestone_list: list[MilestoneType] = strawberry_django.field(
        order=MilestoneOrder,
        filters=MilestoneFilter,
        pagination=True,
    )
    project_list: list[ProjectType] = strawberry_django.field()
    projects_paginated: OffsetPaginated[ProjectType] = (
        strawberry_django.offset_paginated()
    )
    tag_list: list[TagType] = strawberry_django.field()

    favorite_conn: DjangoListConnection[FavoriteType] = strawberry_django.connection()
    issue_conn: DjangoListConnection[
        strawberry.LazyType[
            "IssueType",
            "tests.projects.schema",  # type: ignore  # noqa: F821
        ]
    ] = strawberry_django.connection()
    milestone_conn: DjangoListConnection[MilestoneType] = strawberry_django.connection()

    project_conn: ProjectConnection = strawberry_django.connection()
    tag_conn: DjangoListConnection[TagType] = strawberry_django.connection()
    staff_conn: DjangoListConnection[StaffType] = strawberry_django.connection()

    quiz_list: list[QuizType] = strawberry_django.field()

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
    issue_list_perm_required: list[IssueType] = strawberry_django.field(
        extensions=[HasPerm(perms=["projects.view_issue"])],
    )
    issues_paginated_perm_required: OffsetPaginated[IssueType] = (
        strawberry_django.offset_paginated(
            extensions=[HasPerm(perms=["projects.view_issue"])],
        )
    )
    issue_conn_perm_required: DjangoListConnection[IssueType] = (
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
    issue_list_obj_perm_required: list[IssueType] = strawberry_django.field(
        extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
    )
    issue_list_obj_perm_required_paginated: list[IssueType] = strawberry_django.field(
        extensions=[HasRetvalPerm(perms=["projects.view_issue"])], pagination=True
    )
    issues_paginated_obj_perm_required: OffsetPaginated[IssueType] = (
        strawberry_django.offset_paginated(
            extensions=[HasRetvalPerm(perms=["projects.view_issue"])],
        )
    )
    issue_conn_obj_perm_required: DjangoListConnection[IssueType] = (
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

        return cast("UserType", user)

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
    create_project_with_milestones: ProjectType = mutations.create(
        ProjectInputPartial,
        handle_django_errors=True,
        argument_name="input",
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
            raise ValidationError({"cost": ["Cost cannot be higher than 500"]})
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
            "ProjectType",
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
            "QuizType",
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
