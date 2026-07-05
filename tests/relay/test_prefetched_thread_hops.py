"""Prefetch-optimized nested connections must resolve without per-node thread hops.

Every ``sync_to_async`` call ships work to a worker thread (~0.1-0.2 ms each).
For nested connections the optimizer has already prefetched all data with one
windowed query, so resolving nodes, page info and ``totalCount`` is pure
in-memory work — paying a thread hop per parent node multiplies into hundreds
of hops on list-heavy responses.

The absolute number of hops for the root field depends on the graphql-core
version (graphql-core 3.3+ async-iterates the root queryset, moving the fetch
into Django's own ``sync_to_async``), so the tests assert the actual contract:
the hops (count and call sites) are constant, no matter how many parent nodes
are resolved. Without the optimizer the nested data is not in memory, and the
complementary tests assert that each parent then pays thread hops for its
database work instead of running it on the event loop.
"""

from collections import Counter

import pytest
import strawberry
from asgiref.sync import SyncToAsync, sync_to_async
from strawberry import relay
from strawberry.relay import GlobalID

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoCursorConnection, DjangoListConnection
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


# Building a schema mutates its connection fields (the relay extension
# installs the default resolver on them), so the no-optimizer schemas need
# their own copies of the types instead of reusing the ones above.
@strawberry_django.type(Project, name="ProjectNoOptimizerCursor")
class CursorProjectNoOptimizerType(relay.Node):
    name: str
    milestones: DjangoCursorConnection[MilestoneType] = strawberry_django.connection()

    @classmethod
    def get_queryset(cls, qs, info):
        if not qs.ordered:
            qs = qs.order_by("pk")
        return qs


@strawberry.type
class CursorNoOptimizerQuery:
    projects: DjangoCursorConnection[CursorProjectNoOptimizerType] = (
        strawberry_django.connection()
    )


@strawberry_django.type(Project, name="ProjectWithListConnectionNoOptimizer")
class ListProjectNoOptimizerType(relay.Node):
    name: str
    milestones: DjangoListConnection[MilestoneType] = strawberry_django.connection()


@strawberry.type
class ListConnectionNoOptimizerQuery:
    projects_with_list_connection: list[ListProjectNoOptimizerType] = (
        strawberry_django.field()
    )


# Without the optimizer nothing is prefetched, so nested connections must run
# their queries in worker threads instead of on the event loop.
cursor_schema_no_optimizer = strawberry.Schema(query=CursorNoOptimizerQuery)
list_connection_schema_no_optimizer = strawberry.Schema(
    query=ListConnectionNoOptimizerQuery
)


CURSOR_QUERY = """
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

NO_OPTIMIZER_CURSOR_QUERY = """
query TestQuery {
    projects {
        edges {
          node {
            id
            milestones { totalCount edges { node { id } } }
          }
        }
    }
}
"""

LIST_QUERY = """
query TestQuery {
    projectsWithListConnection {
        id
        milestones { totalCount edges { node { id } } }
    }
}
"""


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


async def _run_and_capture_hops(
    schema, query: str, thread_hops: list[str]
) -> list[str]:
    thread_hops.clear()
    result = await schema.execute(query)
    assert result.errors is None
    assert result.data is not None
    return list(thread_hops)


@pytest.mark.django_db(transaction=True)
async def test_nested_cursor_connection_resolves_prefetched_data_without_hops(
    thread_hops,
):
    await sync_to_async(_create_projects_with_milestones)(1, 2)

    thread_hops.clear()
    result = await cursor_schema.execute(CURSOR_QUERY)

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
    hops_for_two_parents = list(thread_hops)

    # The nested milestones (nodes, page info, totalCount) are served from the
    # prefetch cache on the event loop, so only the root connection may touch
    # the database: adding parents must not add thread hops, and the hops must
    # keep originating from the same (root-only) call sites rather than
    # shifting into nested per-node resolvers.
    await sync_to_async(_create_projects_with_milestones)(3, 3)
    hops_for_five_parents = await _run_and_capture_hops(
        cursor_schema, CURSOR_QUERY, thread_hops
    )

    assert sorted(hops_for_five_parents) == sorted(hops_for_two_parents)


@pytest.mark.django_db(transaction=True)
async def test_nested_list_connection_resolves_prefetched_data_without_hops(
    thread_hops,
):
    await sync_to_async(_create_projects_with_milestones)(1, 2)

    thread_hops.clear()
    result = await list_connection_schema.execute(LIST_QUERY)

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
    hops_for_two_parents = list(thread_hops)

    # The nested milestones are served from the prefetch cache on the event
    # loop, so only fetching the root list may touch the database: adding
    # parents must not add thread hops, and the hops must keep originating
    # from the same (root-only) call sites rather than shifting into nested
    # per-node resolvers.
    await sync_to_async(_create_projects_with_milestones)(3, 3)
    hops_for_five_parents = await _run_and_capture_hops(
        list_connection_schema, LIST_QUERY, thread_hops
    )

    assert sorted(hops_for_five_parents) == sorted(hops_for_two_parents)


@pytest.mark.parametrize(
    ("schema", "query"),
    [
        pytest.param(
            cursor_schema_no_optimizer, NO_OPTIMIZER_CURSOR_QUERY, id="cursor"
        ),
        pytest.param(list_connection_schema_no_optimizer, LIST_QUERY, id="list"),
    ],
)
@pytest.mark.django_db(transaction=True)
async def test_nested_connection_without_prefetch_pays_thread_hops_per_parent(
    schema, query, thread_hops
):
    await sync_to_async(_create_projects_with_milestones)(1, 2)
    hops_for_two_parents = await _run_and_capture_hops(schema, query, thread_hops)

    await sync_to_async(_create_projects_with_milestones)(3, 3)
    hops_for_five_parents = await _run_and_capture_hops(schema, query, thread_hops)

    # Without prefetch optimization the nested querysets are not in memory, so
    # resolving each parent's nested connection (and its totalCount) must ship
    # its database work to a worker thread instead of running it on the event
    # loop: hops scale with the number of parents.
    assert len(hops_for_five_parents) > len(hops_for_two_parents)

    # The extra per-parent hops must be database work: this library's
    # django_resolver wrapping (connection resolution, totalCount) and
    # Django's own queryset-evaluation bridge — proving the work went through
    # sync_to_async rather than being skipped as "async safe".
    extra_call_sites = Counter(hops_for_five_parents) - Counter(hops_for_two_parents)
    assert any(
        site.startswith("strawberry_django.resolvers.") for site in extra_call_sites
    )
    assert all(
        site.startswith(("strawberry_django.", "django.db.models.query."))
        for site in extra_call_sites
    )
