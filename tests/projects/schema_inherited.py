from typing import Optional

import strawberry

import strawberry_django
from strawberry_django import mutations

from .models import Issue, Milestone, Project
from .schema import IssueInput, IssueType, MilestoneType, ProjectType


@strawberry_django.type(Project)
class ProjectTypeSubclass(ProjectType): ...


@strawberry_django.type(Milestone)
class MilestoneTypeSubclass(MilestoneType): ...


@strawberry_django.input(Issue)
class IssueInputSubclass(IssueInput): ...


@strawberry.type
class Query:
    project: Optional[ProjectTypeSubclass] = strawberry_django.node()
    milestone: Optional[MilestoneTypeSubclass] = strawberry_django.node()


@strawberry.type
class Mutation:
    create_issue: IssueType = mutations.create(
        IssueInputSubclass,
        handle_django_errors=True,
        argument_name="input",
    )


schema = strawberry.Schema(query=Query, mutation=Mutation)
