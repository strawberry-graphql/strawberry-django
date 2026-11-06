from collections.abc import AsyncGenerator
from typing import cast

import pytest
import strawberry
from asgiref.sync import async_to_sync
from django.db.models import QuerySet
from strawberry import auto, relay

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension, optimizer
from strawberry_django.relay import DjangoListConnection
from tests.projects.faker import IssueFactory, MilestoneFactory
from tests.projects.models import Issue, Milestone
from tests.utils import assert_num_queries


@strawberry_django.type(Milestone)
class MilestoneType(relay.Node):
    name: auto


@strawberry_django.type(Issue)
class IssueType(relay.Node):
    name: auto
    milestone: MilestoneType


@strawberry.type
class IssuesChanged:
    @strawberry_django.field
    def issues(self) -> list[IssueType]:
        return cast("list[IssueType]", Issue.objects.all())

    @strawberry_django.field
    async def async_issues(self) -> list[IssueType]:
        return cast("list[IssueType]", Issue.objects.all())

    @strawberry_django.connection(DjangoListConnection[IssueType])
    def connection(self) -> QuerySet[Issue]:
        return Issue.objects.all()


@strawberry.type
class Query:
    @strawberry.field
    def noop(self) -> bool:
        return True


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def issues_changed(self) -> AsyncGenerator[IssuesChanged, None]:
        yield IssuesChanged()
        yield IssuesChanged()


schema = strawberry.Schema(
    query=Query,
    subscription=Subscription,
    extensions=[DjangoOptimizerExtension],
)


def create_issues():
    milestone = MilestoneFactory.create()
    IssueFactory.create_batch(3, milestone=milestone)
    return milestone


def collect(query: str):
    async def consume():
        result = await schema.subscribe(query)
        return [event async for event in result]

    # async_to_sync keeps the sync_to_async hops on this thread, which is the one
    # holding the database connection that assert_num_queries is capturing
    return async_to_sync(consume)()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("field", ["issues", "asyncIssues"])
def test_subscription_optimizes_querysets_on_every_event(field: str):
    milestone = create_issues()
    query = f"subscription {{ issuesChanged {{ {field} {{ name milestone {{ name }} }} }} }}"

    # One query per event, with the milestones coming from a select_related
    with assert_num_queries(2):
        events = collect(query)

    assert len(events) == 2
    for event in events:
        assert event.errors is None
        assert event.data is not None
        issues = event.data["issuesChanged"][field]
        assert len(issues) == 3
        assert {issue["milestone"]["name"] for issue in issues} == {milestone.name}


@pytest.mark.django_db(transaction=True)
def test_subscription_optimizes_sibling_fields_resolved_concurrently():
    milestone = create_issues()
    query = """
    subscription {
      issuesChanged {
        issues { name milestone { name } }
        asyncIssues { name milestone { name } }
      }
    }
    """

    # One query per field on each event
    with assert_num_queries(4):
        events = collect(query)

    assert len(events) == 2
    for event in events:
        assert event.errors is None
        assert event.data is not None
        for field in ("issues", "asyncIssues"):
            issues = event.data["issuesChanged"][field]
            assert {issue["milestone"]["name"] for issue in issues} == {milestone.name}


@pytest.mark.django_db(transaction=True)
def test_subscription_optimizes_connections_on_every_event():
    milestone = create_issues()
    query = """
    subscription {
      issuesChanged {
        connection { edges { node { name milestone { name } } } }
      }
    }
    """

    with assert_num_queries(2):
        events = collect(query)

    assert len(events) == 2
    for event in events:
        assert event.errors is None
        assert event.data is not None
        edges = event.data["issuesChanged"]["connection"]["edges"]
        assert len(edges) == 3
        assert {edge["node"]["milestone"]["name"] for edge in edges} == {milestone.name}


@pytest.mark.django_db(transaction=True)
def test_subscription_respects_disabled_optimizer():
    create_issues()
    query = "subscription { issuesChanged { issues { name milestone { name } } } }"

    # One query for the issues plus one per issue for its milestone, on each event
    with DjangoOptimizerExtension.disabled(), assert_num_queries(8):
        events = collect(query)

    assert all(event.errors is None for event in events)


@pytest.mark.django_db(transaction=True)
def test_subscription_does_not_leak_optimizer_outside_of_field_resolution():
    create_issues()
    query = "subscription { issuesChanged { issues { name } } }"

    async def consume():
        result = await schema.subscribe(query)
        return [optimizer.get() async for _ in result]

    assert async_to_sync(consume)() == [None, None]
