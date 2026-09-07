import pathlib

import strawberry
from graphql import parse
from pytest_snapshot.plugin import Snapshot

import strawberry_django
from strawberry_django import mutations
from tests.conftest import normalize_sdl

from .models import Issue, Milestone, Project
from .schema import IssueInput, IssueType, MilestoneType, ProjectType, schema

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_schema():
    # Directive argument types moved into the sorted type map in Strawberry
    # 0.326.0. Compare definitions without depending on their printed order;
    # fields, arguments, descriptions and directive applications still match.
    actual = parse(normalize_sdl(str(schema)), no_location=True)
    expected = parse(
        normalize_sdl((SNAPSHOTS_DIR / "schema.gql").read_text()), no_location=True
    )

    def definition_key(definition):
        return definition.kind, getattr(getattr(definition, "name", None), "value", "")

    assert sorted(actual.definitions, key=definition_key) == sorted(
        expected.definitions, key=definition_key
    )


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
