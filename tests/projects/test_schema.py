import pathlib

import strawberry
from pytest_snapshot.plugin import Snapshot

import strawberry_django
from strawberry_django import mutations
from tests.conftest import normalize_sdl

from .models import Issue, Milestone, Project
from .schema import IssueInput, IssueType, MilestoneType, ProjectType, schema

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_schema(snapshot: Snapshot):
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    snapshot.assert_match(normalize_sdl(str(schema)), "schema.gql")


def test_schema_with_inheritance(snapshot: Snapshot):
    @strawberry_django.type(Project)
    class ProjectTypeSubclass(ProjectType): ...

    @strawberry_django.type(Milestone)
    class MilestoneTypeSubclass(MilestoneType): ...

    @strawberry_django.input(Issue)
    class IssueInputSubclass(IssueInput): ...

    @strawberry.type
    class Query:
        project: ProjectTypeSubclass | None = strawberry_django.node()
        milestone: MilestoneTypeSubclass | None = strawberry_django.node()

    @strawberry.type
    class Mutation:
        create_issue: IssueType = mutations.create(
            IssueInputSubclass,
            handle_django_errors=True,
            argument_name="input",
        )

    schema = strawberry.Schema(query=Query, mutation=Mutation)
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    snapshot.assert_match(normalize_sdl(str(schema)), "schema_with_inheritance.gql")
