import dataclasses
from typing import cast

import pytest
import strawberry
from asgiref.sync import async_to_sync
from strawberry import auto, relay
from strawberry.types import ExecutionResult
from strawberry.types.maybe import Maybe

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import DjangoListConnection
from tests.projects.faker import IssueFactory, MilestoneFactory
from tests.projects.models import Issue, Milestone
from tests.utils import assert_num_queries


@strawberry_django.type(Milestone)
class MilestoneType(relay.Node):
    name: auto


@strawberry_django.filter_type(Issue, lookups=True)
class IssueFilter:
    name: auto


@strawberry_django.type(Issue, filters=IssueFilter)
class IssueType(relay.Node):
    name: auto
    milestone: MilestoneType


@strawberry_django.input(Issue)
class IssueInput:
    name: auto
    milestone: auto


@strawberry_django.partial(Issue)
class IssueInputPartial(IssueInput):
    id: auto


@strawberry.type
class IssueQuery:
    issues: list[IssueType] = strawberry_django.field()
    issues_paginated: OffsetPaginated[IssueType] = strawberry_django.offset_paginated()
    issues_connection: DjangoListConnection[IssueType] = strawberry_django.connection()
    issue: IssueType = strawberry_django.node()


@strawberry.type
class IssueMutation:
    create_issue: IssueType = strawberry_django.mutations.create(IssueInput)
    update_issue: IssueType = strawberry_django.mutations.update(IssueInputPartial)
    delete_issue: IssueType = strawberry_django.mutations.delete(
        strawberry_django.NodeInput
    )


@strawberry.type
class Query:
    @strawberry.field
    def issues(self) -> IssueQuery:
        return IssueQuery()

    @strawberry.field
    def first_issue(self) -> IssueQuery:
        return IssueQuery(
            issues=cast("list[IssueType]", Issue.objects.order_by("pk")[:1]),
            issues_connection=cast(
                "DjangoListConnection[IssueType]",
                Issue.objects.order_by("pk")[:1],
            ),
        )


@strawberry.type
class Mutation:
    @strawberry.field
    def issues(self) -> IssueMutation:
        return IssueMutation()


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[DjangoOptimizerExtension],
)


def execute(query: str, *, is_async: bool) -> ExecutionResult:
    if is_async:
        # async_to_sync keeps the sync_to_async hops on this thread, which is the
        # one holding the database connection that assert_num_queries is capturing
        return async_to_sync(schema.execute)(query)

    return schema.execute_sync(query)


def create_issues() -> tuple[Milestone, list[Issue]]:
    milestone = MilestoneFactory.create()
    return milestone, IssueFactory.create_batch(3, milestone=milestone)


def test_namespace_type_can_be_instantiated_without_values():
    namespace = IssueQuery()
    for field in dataclasses.fields(namespace):
        assert getattr(namespace, field.name) is strawberry.UNSET

    assert IssueMutation() is not None


def test_maybe_django_field_in_input_defaults_to_none():
    @strawberry_django.input(Issue)
    class Input:
        name: Maybe[str] = strawberry_django.field()
        priority: int | None = strawberry_django.field()

    fields = {f.name: f for f in dataclasses.fields(Input)}
    assert fields["name"].default is None
    assert fields["priority"].default is strawberry.UNSET


@pytest.mark.parametrize(
    "base_decorator", [strawberry_django.type(Issue), strawberry.type]
)
def test_maybe_field_inherited_from_django_field_defaults_to_none(base_decorator):
    @base_decorator
    class Base:
        title: str = strawberry_django.field(field_name="name")
        priority: int = strawberry_django.field()

    @strawberry_django.input(Issue)
    class Input(Base):
        title: Maybe[str]  # type: ignore

    fields = {f.name: f for f in dataclasses.fields(Input)}
    assert fields["title"].default is None
    assert getattr(fields["title"], "django_name", None) == "name"
    assert fields["priority"].default is strawberry.UNSET


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_list(is_async: bool):
    milestone, issues = create_issues()
    query = "{ issues { issues { name milestone { name } } } }"

    # A single query, with the milestones coming from a select_related
    with assert_num_queries(1):
        result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {
        "issues": {
            "issues": [
                {"name": issue.name, "milestone": {"name": milestone.name}}
                for issue in issues
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_list_with_filters(is_async: bool):
    _, issues = create_issues()
    query = f"""
    {{
      issues {{
        issues(filters: {{ name: {{ exact: "{issues[1].name}" }} }}) {{ name }}
      }}
    }}
    """

    result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {"issues": {"issues": [{"name": issues[1].name}]}}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_offset_paginated(is_async: bool):
    milestone, issues = create_issues()
    query = """
    {
      issues {
        issuesPaginated(pagination: { limit: 2 }) {
          totalCount
          results { name milestone { name } }
        }
      }
    }
    """

    result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {
        "issues": {
            "issuesPaginated": {
                "totalCount": 3,
                "results": [
                    {"name": issue.name, "milestone": {"name": milestone.name}}
                    for issue in issues[:2]
                ],
            },
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_connection(is_async: bool):
    milestone, issues = create_issues()
    query = """
    {
      issues {
        issuesConnection {
          totalCount
          edges { node { name milestone { name } } }
        }
      }
    }
    """

    result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {
        "issues": {
            "issuesConnection": {
                "totalCount": 3,
                "edges": [
                    {
                        "node": {
                            "name": issue.name,
                            "milestone": {"name": milestone.name},
                        },
                    }
                    for issue in issues
                ],
            },
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_node(is_async: bool):
    _, issues = create_issues()
    issue = issues[1]
    global_id = relay.to_base64("IssueType", issue.pk)
    query = f'{{ issues {{ issue(id: "{global_id}") {{ name }} }} }}'

    result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {"issues": {"issue": {"name": issue.name}}}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_fields_use_given_values(is_async: bool):
    _, issues = create_issues()
    issue = issues[0]
    query = """
    {
      firstIssue {
        issues { name }
        issuesConnection { edges { node { name } } }
      }
    }
    """

    result = execute(query, is_async=is_async)

    assert result.errors is None
    assert result.data == {
        "firstIssue": {
            "issues": [{"name": issue.name}],
            "issuesConnection": {"edges": [{"node": {"name": issue.name}}]},
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("is_async", [False, True])
def test_namespaced_mutations(is_async: bool):
    milestone = MilestoneFactory.create()

    result = execute(
        f"""
        mutation {{
          issues {{
            createIssue(data: {{ name: "New", milestone: {{ set: "{milestone.pk}" }} }}) {{
              id
              name
              milestone {{ name }}
            }}
          }}
        }}
        """,
        is_async=is_async,
    )
    assert result.errors is None
    assert isinstance(result.data, dict)
    created = result.data["issues"]["createIssue"]
    assert created["name"] == "New"
    assert created["milestone"] == {"name": milestone.name}

    issue = Issue.objects.get(milestone=milestone)
    result = execute(
        f"""
        mutation {{
          issues {{
            updateIssue(data: {{ id: "{issue.pk}", name: "Updated" }}) {{ name }}
          }}
        }}
        """,
        is_async=is_async,
    )
    assert result.errors is None
    assert result.data == {"issues": {"updateIssue": {"name": "Updated"}}}
    issue.refresh_from_db()
    assert issue.name == "Updated"

    result = execute(
        f"""
        mutation {{
          issues {{
            deleteIssue(data: {{ id: "{created["id"]}" }}) {{ name }}
          }}
        }}
        """,
        is_async=is_async,
    )
    assert result.errors is None
    assert result.data == {"issues": {"deleteIssue": {"name": "Updated"}}}
    assert not Issue.objects.filter(pk=issue.pk).exists()
