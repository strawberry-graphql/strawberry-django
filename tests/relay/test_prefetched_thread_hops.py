"""Prefetch-optimized nested connections must resolve without per-node thread hops.

Every ``sync_to_async`` call ships work to a worker thread (~0.1-0.2 ms each).
For nested connections the optimizer has already prefetched all data with one
windowed query, so resolving nodes, page info and ``totalCount`` is pure
in-memory work — paying a thread hop per parent node multiplies into hundreds
of hops on list-heavy responses.

The absolute number of hops for the root field depends on the graphql-core
version (graphql-core 3.3+ async-iterates the root queryset, moving the fetch
into Django's own ``sync_to_async``), so the tests assert the actual contract:
the hop count is constant, no matter how many parent nodes are resolved.
"""

import pytest
import strawberry
from asgiref.sync import SyncToAsync, sync_to_async
from strawberry import relay
from strawberry.relay import GlobalID

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoListConnection
from tests.projects.models import Milestone, Project

from .test_cursor_pagination import MilestoneType
from .test_cursor_pagination import schema as cursor_schema


@strawberry_django.type(Project, name="ProjectWithListConnection")
class ProjectWithListConnectionType(relay.Node):
    name: str
    milestones: DjangoListConnection[MilestoneType] = strawberry_django.connection()


@strawberry.type
class ListConnectionQuery:
    projects_with_list_connection: list[ProjectWithListConnectionType] = (
        strawberry_django.field()
    )


list_connection_schema = strawberry.Schema(
    query=ListConnectionQuery, extensions=[DjangoOptimizerExtension()]
)


@pytest.fixture
def thread_hops(monkeypatch):
    hops: list[str] = []
    orig_call = SyncToAsync.__call__

    async def counting_call(self, *args, **kwargs):
        func = self.func
        hops.append(
            f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', '?')}"
        )
        return await orig_call(self, *args, **kwargs)

    monkeypatch.setattr(SyncToAsync, "__call__", counting_call)
    return hops


def _create_projects_with_milestones(first_project_id: int, count: int) -> None:
    for project_id in range(first_project_id, first_project_id + count):
        project = Project.objects.create(id=project_id, name=f"Project {project_id}")
        Milestone.objects.create(id=project_id * 10, project=project)
        Milestone.objects.create(id=project_id * 10 + 1, project=project)


async def _count_hops(schema, query: str, thread_hops: list[str]) -> int:
    thread_hops.clear()
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data is not None
    return len(thread_hops)


@pytest.mark.django_db(transaction=True)
async def test_nested_cursor_connection_resolves_prefetched_data_without_hops(
    thread_hops,
):
    await sync_to_async(_create_projects_with_milestones)(1, 2)

    query = """
    query TestQuery {
        projects(order: { id: ASC }) {
            edges {
              node {
                id
                milestones { totalCount edges { node { id } } }
              }
            }
        }
    }
    """

    thread_hops.clear()
    result = await cursor_schema.execute(query)

    assert result.errors is None
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "id": str(GlobalID("ProjectType", str(project_id))),
                        "milestones": {
                            "totalCount": 2,
                            "edges": [
                                {
                                    "node": {
                                        "id": str(
                                            GlobalID("MilestoneType", str(milestone_id))
                                        )
                                    }
                                }
                                for milestone_id in (
                                    project_id * 10,
                                    project_id * 10 + 1,
                                )
                            ],
                        },
                    }
                }
                for project_id in (1, 2)
            ],
        }
    }
    hops_for_two_parents = len(thread_hops)

    # The nested milestones (nodes, page info, totalCount) are served from the
    # prefetch cache on the event loop, so only the root connection may touch
    # the database: adding parents must not add thread hops.
    await sync_to_async(_create_projects_with_milestones)(3, 3)
    hops_for_five_parents = await _count_hops(cursor_schema, query, thread_hops)

    assert hops_for_five_parents == hops_for_two_parents, thread_hops


@pytest.mark.django_db(transaction=True)
async def test_nested_list_connection_resolves_prefetched_data_without_hops(
    thread_hops,
):
    await sync_to_async(_create_projects_with_milestones)(1, 2)

    query = """
    query TestQuery {
        projectsWithListConnection {
            id
            milestones { totalCount edges { node { id } } }
        }
    }
    """

    thread_hops.clear()
    result = await list_connection_schema.execute(query)

    assert result.errors is None
    assert result.data == {
        "projectsWithListConnection": [
            {
                "id": str(GlobalID("ProjectWithListConnection", str(project_id))),
                "milestones": {
                    "totalCount": 2,
                    "edges": [
                        {
                            "node": {
                                "id": str(GlobalID("MilestoneType", str(milestone_id)))
                            }
                        }
                        for milestone_id in (project_id * 10, project_id * 10 + 1)
                    ],
                },
            }
            for project_id in (1, 2)
        ],
    }
    hops_for_two_parents = len(thread_hops)

    # The nested milestones are served from the prefetch cache on the event
    # loop, so only fetching the root list may touch the database: adding
    # parents must not add thread hops.
    await sync_to_async(_create_projects_with_milestones)(3, 3)
    hops_for_five_parents = await _count_hops(
        list_connection_schema, query, thread_hops
    )

    assert hops_for_five_parents == hops_for_two_parents, thread_hops
