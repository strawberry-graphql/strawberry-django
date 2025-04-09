import datetime
from typing import Optional, cast

import pytest
import strawberry
from django.db.models import F, OrderBy, QuerySet, Value
from django.db.models.aggregates import Count
from strawberry.relay import GlobalID, Node, to_base64

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay_cursor import (
    DjangoCursorConnection,
    DjangoCursorEdge,
)
from tests.projects.models import Milestone, Project
from tests.utils import assert_num_queries


@strawberry_django.order(Project)
class ProjectOrder:
    id: strawberry.auto
    name: strawberry.auto
    due_date: strawberry.auto

    @strawberry_django.order_field()
    def milestone_count(
        self, queryset: QuerySet, value: strawberry_django.Ordering, prefix: str
    ) -> "tuple[QuerySet, list[OrderBy]]":
        queryset = queryset.annotate(_milestone_count=Count(f"{prefix}milestone"))
        return queryset, [value.resolve("_milestone_count")]


@strawberry_django.order(Milestone)
class MilestoneOrder:
    due_date: strawberry.auto
    project: ProjectOrder

    @strawberry_django.order_field()
    def days_left(
        self, queryset: QuerySet, value: strawberry_django.Ordering, prefix: str
    ) -> "tuple[QuerySet, list[OrderBy]]":
        queryset = queryset.alias(
            _days_left=Value(datetime.date(2025, 12, 31)) - F(f"{prefix}due_date")
        )
        return queryset, [value.resolve("_days_left")]


@strawberry_django.type(Milestone, order=MilestoneOrder)
class MilestoneType(Node):
    due_date: strawberry.auto
    project: "ProjectType"

    @classmethod
    def get_queryset(cls, qs: QuerySet, info):
        if not qs.ordered:
            qs = qs.order_by("project__name", "pk")
        return qs


@strawberry_django.type(Project, order=ProjectOrder)
class ProjectType(Node):
    name: str
    due_date: datetime.date
    milestones: DjangoCursorConnection[MilestoneType] = strawberry_django.connection()

    @classmethod
    def get_queryset(cls, qs: QuerySet, info):
        if not qs.ordered:
            qs = qs.order_by("name", "pk")
        return qs


@strawberry.type()
class Query:
    project: Optional[ProjectType] = strawberry_django.node()
    projects: DjangoCursorConnection[ProjectType] = strawberry_django.connection()
    milestones: DjangoCursorConnection[MilestoneType] = strawberry_django.connection()

    @strawberry_django.connection(DjangoCursorConnection[ProjectType])
    @staticmethod
    def projects_with_resolver() -> list[ProjectType]:
        return cast("list[ProjectType]", Project.objects.all().order_by("-pk"))


schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension()])


@pytest.fixture
def test_objects():
    pa = Project.objects.create(id=1, name="Project A")
    pc1 = Project.objects.create(id=2, name="Project C")
    Project.objects.create(id=5, name="Project C")
    pb = Project.objects.create(id=3, name="Project B")
    Project.objects.create(id=6, name="Project D")
    Project.objects.create(id=4, name="Project E")

    Milestone.objects.create(id=1, project=pb, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=2, project=pb, due_date=datetime.date(2025, 6, 2))
    Milestone.objects.create(id=3, project=pc1, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=4, project=pa, due_date=datetime.date(2025, 6, 5))


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination(test_objects):
    query = """
    query TestQuery {
        projects {
            edges {
                cursor
                node { id name }
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(query)
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "name": "Project A",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project B","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                            "name": "Project B",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","5"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "5")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project E","4"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                            "name": "Project E",
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_custom_resolver(test_objects):
    query = """
    query TestQuery($after: String, $first: Int) {
        projectsWithResolver(after: $after, first: $first) {
            edges {
                cursor
                node { id name }
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "after": to_base64(DjangoCursorEdge.PREFIX, '["6"]'),
                "first": 2,
            },
        )
        assert result.data == {
            "projectsWithResolver": {
                "edges": [
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["5"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "5")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["4"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                            "name": "Project E",
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_forward_pagination(test_objects):
    query = """
    query TestQuery($first: Int, $after: String) {
        projects(first: $first, after: $after) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasNextPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "first": 3,
                "after": to_base64(DjangoCursorEdge.PREFIX, '["Project B","3"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project C","2"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project D","6"]'
                    ),
                    "hasNextPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","5"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "5")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_forward_pagination_first_page(test_objects):
    query = """
    query TestQuery($first: Int, $after: String) {
        projects(first: $first, after: $after) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "first": 1,
                "after": None,
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project A","1"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project A","1"]'
                    ),
                    "hasPreviousPage": False,
                    "hasNextPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "name": "Project A",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_forward_pagination_last_page(test_objects):
    query = """
    query TestQuery($first: Int, $after: String) {
        projects(first: $first, after: $after) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasNextPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "first": 10,
                "after": to_base64(DjangoCursorEdge.PREFIX, '["Project D","6"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project E","4"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project E","4"]'
                    ),
                    "hasNextPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project E","4"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                            "name": "Project E",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_backward_pagination(test_objects):
    query = """
    query TestQuery($last: Int, $before: String) {
        projects(last: $last, before: $before) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "last": 2,
                "before": to_base64(DjangoCursorEdge.PREFIX, '["Project C","5"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project B","3"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project C","2"]'
                    ),
                    "hasPreviousPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project B","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                            "name": "Project B",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_backward_pagination_first_page(test_objects):
    query = """
    query TestQuery($last: Int, $before: String) {
        projects(last: $last, before: $before) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasNextPage
              hasPreviousPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "last": 2,
                "before": None,
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project D","6"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project E","4"]'
                    ),
                    "hasPreviousPage": True,
                    "hasNextPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project E","4"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                            "name": "Project E",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_backward_pagination_last_page(test_objects):
    query = """
    query TestQuery($last: Int, $before: String) {
        projects(last: $last, before: $before) {
            edges {
                cursor
                node { id name }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "last": 2,
                "before": to_base64(DjangoCursorEdge.PREFIX, '["Project C","2"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project A","1"]'
                    ),
                    "endCursor": to_base64(
                        DjangoCursorEdge.PREFIX, '["Project B","3"]'
                    ),
                    "hasPreviousPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "name": "Project A",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project B","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                            "name": "Project B",
                        },
                    },
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_custom_order(test_objects):
    query = """
    query TestQuery($first: Int, $after: String) {
        projects(first: $first, after: $after, order: { name: DESC id: ASC }) {
            edges {
                cursor
                node { id name }
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "first": 2,
                "after": to_base64(DjangoCursorEdge.PREFIX, '["Project E","4"]'),
            },
        )
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_joined_field_order(test_objects):
    query = """
    query TestQuery {
        milestones(order: { dueDate: DESC, project: { name: ASC } }) {
            edges {
                cursor
                node { id dueDate project { id name } }
            }
        }
    }
    """
    with assert_num_queries(2):
        result = schema.execute_sync(query)
        assert result.data == {
            "milestones": {
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX,
                            '["2025-06-05","Project A","4"]',
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "4")),
                            "dueDate": "2025-06-05",
                            "project": {
                                "id": str(GlobalID("ProjectType", "1")),
                                "name": "Project A",
                            },
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX,
                            '["2025-06-02","Project B","2"]',
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "2")),
                            "dueDate": "2025-06-02",
                            "project": {
                                "id": str(GlobalID("ProjectType", "3")),
                                "name": "Project B",
                            },
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX,
                            '["2025-06-01","Project B","1"]',
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "1")),
                            "dueDate": "2025-06-01",
                            "project": {
                                "id": str(GlobalID("ProjectType", "3")),
                                "name": "Project B",
                            },
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX,
                            '["2025-06-01","Project C","3"]',
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "3")),
                            "dueDate": "2025-06-01",
                            "project": {
                                "id": str(GlobalID("ProjectType", "2")),
                                "name": "Project C",
                            },
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_expression_order(test_objects):
    query = """
    query TestQuery($after: String) {
        milestones(after: $after, order: { daysLeft: ASC }) {
            edges {
                cursor
                node { id }
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {"after": to_base64(DjangoCursorEdge.PREFIX, '["209 00:00:00","4"]')},
        )
        assert result.data == {
            "milestones": {
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["212 00:00:00","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "2")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["213 00:00:00","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "1")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["213 00:00:00","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "3")),
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_agg_expression_order(test_objects):
    query = """
    query TestQuery($after: String, $first: Int) {
        projects(after: $after, first: $first, order: { milestoneCount: DESC }) {
            edges {
                cursor
                node { id }
            }
        }
    }
    """
    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "after": None,
                "first": 4,
            },
        )
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["2","3"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                        },
                    },
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["1","1"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                        },
                    },
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["1","2"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                        },
                    },
                    {
                        "cursor": to_base64(DjangoCursorEdge.PREFIX, '["0","4"]'),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("order", "pks"),
    [
        ("DESC_NULLS_FIRST", [1, 4, 3, 2]),
        ("DESC_NULLS_LAST", [3, 2, 1, 4]),
        ("ASC_NULLS_FIRST", [1, 4, 2, 3]),
        ("ASC_NULLS_LAST", [2, 3, 1, 4]),
    ],
)
@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_cursor_pagination_order_with_nulls(order, pks, offset):
    pa = Project.objects.create(id=1, name="Project A", due_date=None)
    pc = Project.objects.create(
        id=2, name="Project C", due_date=datetime.date(2025, 6, 2)
    )
    pb = Project.objects.create(
        id=3, name="Project B", due_date=datetime.date(2025, 6, 5)
    )
    pd = Project.objects.create(id=4, name="Project D", due_date=None)
    projects_lookup = {p.pk: p for p in (pa, pb, pc, pd)}
    projects = [projects_lookup[pk] for pk in pks]
    query = """
    query TestQuery($after: String, $first: Int, $order: Ordering!) {
        projects(after: $after, first: $first, order: { dueDate: $order }) {
            edges {
                cursor
                node { id name }
            }
        }
    }
    """

    def make_cursor(project: Project) -> str:
        due_date_part = (
            f'"{project.due_date.isoformat()}"' if project.due_date else "null"
        )
        return to_base64(DjangoCursorEdge.PREFIX, f'[{due_date_part},"{project.pk}"]')

    with assert_num_queries(1):
        result = schema.execute_sync(
            query,
            {
                "order": order,
                "after": make_cursor(projects[offset]),
                "first": 2,
            },
        )
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": make_cursor(project),
                        "node": {
                            "id": str(GlobalID("ProjectType", str(project.pk))),
                            "name": project.name,
                        },
                    }
                    for project in projects[offset + 1 : offset + 3]
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
async def test_cursor_pagination_async(test_objects):
    query = """
    query TestQuery {
        projects {
            edges {
                cursor
                node { id name }
            }
        }
    }
    """
    result = await schema.execute(query)
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project A","1"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "1")),
                        "name": "Project A",
                    },
                },
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project B","3"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "3")),
                        "name": "Project B",
                    },
                },
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project C","2"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "2")),
                        "name": "Project C",
                    },
                },
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project C","5"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "5")),
                        "name": "Project C",
                    },
                },
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project D","6"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "6")),
                        "name": "Project D",
                    },
                },
                {
                    "cursor": to_base64(DjangoCursorEdge.PREFIX, '["Project E","4"]'),
                    "node": {
                        "id": str(GlobalID("ProjectType", "4")),
                        "name": "Project E",
                    },
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_cursor_pagination_in_single():
    pa = Project.objects.create(id=1, name="Project A")
    pb = Project.objects.create(id=2, name="Project B")

    Milestone.objects.create(id=1, project=pb, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=2, project=pb, due_date=datetime.date(2025, 6, 2))
    Milestone.objects.create(id=3, project=pb, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=4, project=pa, due_date=datetime.date(2025, 6, 5))
    Milestone.objects.create(id=5, project=pa, due_date=datetime.date(2025, 6, 1))

    query = """
    query TestQuery($id: GlobalID!) {
        project(id: $id) {
            id
                  milestones(first: 2, order: { dueDate: ASC }) {
                    edges {
                      cursor
                      node { id dueDate }
                    }
                  }
        }
    }
    """
    with assert_num_queries(2):
        result = schema.execute_sync(query, {"id": str(GlobalID("ProjectType", "2"))})
        assert result.data == {
            "project": {
                "id": str(GlobalID("ProjectType", "2")),
                "milestones": {
                    "edges": [
                        {
                            "cursor": to_base64(
                                DjangoCursorEdge.PREFIX,
                                '["2025-06-01","1"]',
                            ),
                            "node": {
                                "id": str(GlobalID("MilestoneType", "1")),
                                "dueDate": "2025-06-01",
                            },
                        },
                        {
                            "cursor": to_base64(
                                DjangoCursorEdge.PREFIX,
                                '["2025-06-01","3"]',
                            ),
                            "node": {
                                "id": str(GlobalID("MilestoneType", "3")),
                                "dueDate": "2025-06-01",
                            },
                        },
                    ]
                },
            },
        }


@pytest.mark.django_db(transaction=True)
def test_nested_cursor_pagination():
    pa = Project.objects.create(id=1, name="Project A")
    pb = Project.objects.create(id=2, name="Project B")

    Milestone.objects.create(id=1, project=pb, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=2, project=pb, due_date=datetime.date(2025, 6, 2))
    Milestone.objects.create(id=3, project=pb, due_date=datetime.date(2025, 6, 1))
    Milestone.objects.create(id=4, project=pa, due_date=datetime.date(2025, 6, 5))
    Milestone.objects.create(id=5, project=pa, due_date=datetime.date(2025, 6, 1))

    query = """
    query TestQuery {
        projects {
            edges {
                cursor
                node {
                  id
                  milestones(first: 2, order: { dueDate: ASC }) {
                    edges {
                      cursor
                      node { id dueDate }
                    }
                  }
                }
            }
        }
    }
    """
    with assert_num_queries(2):
        result = schema.execute_sync(query)
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "milestones": {
                                "edges": [
                                    {
                                        "cursor": to_base64(
                                            DjangoCursorEdge.PREFIX,
                                            '["2025-06-01","5"]',
                                        ),
                                        "node": {
                                            "id": str(GlobalID("MilestoneType", "5")),
                                            "dueDate": "2025-06-01",
                                        },
                                    },
                                    {
                                        "cursor": to_base64(
                                            DjangoCursorEdge.PREFIX,
                                            '["2025-06-05","4"]',
                                        ),
                                        "node": {
                                            "id": str(GlobalID("MilestoneType", "4")),
                                            "dueDate": "2025-06-05",
                                        },
                                    },
                                ]
                            },
                        },
                    },
                    {
                        "cursor": to_base64(
                            DjangoCursorEdge.PREFIX, '["Project B","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "milestones": {
                                "edges": [
                                    {
                                        "cursor": to_base64(
                                            DjangoCursorEdge.PREFIX,
                                            '["2025-06-01","1"]',
                                        ),
                                        "node": {
                                            "id": str(GlobalID("MilestoneType", "1")),
                                            "dueDate": "2025-06-01",
                                        },
                                    },
                                    {
                                        "cursor": to_base64(
                                            DjangoCursorEdge.PREFIX,
                                            '["2025-06-01","3"]',
                                        ),
                                        "node": {
                                            "id": str(GlobalID("MilestoneType", "3")),
                                            "dueDate": "2025-06-01",
                                        },
                                    },
                                ]
                            },
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "cursor",
    [
        *(
            to_base64(DjangoCursorEdge.PREFIX, c)
            for c in ("", "[]", "[1]", "{}", "foo", '["foo"]')
        ),
        to_base64("foo", "bar"),
        to_base64("foo", '["1"]'),
    ],
)
def test_invalid_cursor(cursor, test_objects):
    query = """
    query TestQuery($after: String) {
        projects(after: $after, order: { id: ASC }) {
            edges {
                cursor
                node {
                  id
                }
            }
        }
    }
    """
    result = schema.execute_sync(query, {"after": cursor})
    assert result.data is None
    assert result.errors
    assert result.errors[0].message == "Invalid cursor"
