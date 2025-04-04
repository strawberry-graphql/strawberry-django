import datetime

import pytest
import strawberry
from django.db.models import F, QuerySet, Value
from django.db.models.aggregates import Count
from strawberry import Schema
from strawberry.relay import GlobalID, Node, to_base64

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay_cursor import (
    DjangoCursorConnection,
    OrderedCollectionCursor,
)
from tests.projects.models import Milestone, Project
from tests.utils import assert_num_queries


@pytest.fixture
def schema() -> Schema:
    @strawberry_django.order(Project)
    class ProjectOrder:
        id: strawberry.auto
        name: strawberry.auto

        @strawberry_django.order_field()
        def milestone_count(
            self, queryset: QuerySet, value: strawberry_django.Ordering, prefix: str
        ) -> tuple[QuerySet, list[str]] | list[str]:
            queryset = queryset.annotate(_milestone_count=Count(f"{prefix}milestone"))
            return queryset, [value.resolve("_milestone_count")]

    @strawberry_django.type(Project, order=ProjectOrder)
    class ProjectType(Node):
        name: str

        @classmethod
        def get_queryset(cls, qs: QuerySet, info):
            if not qs.ordered:
                qs = qs.order_by("name", "pk")
            return qs

    @strawberry_django.order(Milestone)
    class MilestoneOrder:
        due_date: strawberry.auto
        project: ProjectOrder

        @strawberry_django.order_field()
        def days_left(
            self, queryset: QuerySet, value: strawberry_django.Ordering, prefix: str
        ) -> tuple[QuerySet, list[str]] | list[str]:
            queryset = queryset.alias(
                _days_left=Value(datetime.date(2025, 12, 31)) - F(f"{prefix}due_date")
            )
            return queryset, [value.resolve("_days_left")]

    @strawberry_django.type(Milestone, order=MilestoneOrder)
    class MilestoneType(Node):
        due_date: strawberry.auto
        project: ProjectType

        @classmethod
        def get_queryset(cls, qs: QuerySet, info):
            if not qs.ordered:
                qs = qs.order_by("project__name", "pk")
            return qs

    @strawberry.type()
    class Query:
        projects: DjangoCursorConnection[ProjectType] = strawberry_django.connection()
        milestones: DjangoCursorConnection[MilestoneType] = (
            strawberry_django.connection()
        )

    return strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension()])


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
def test_cursor_pagination(schema: Schema, test_objects):
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
                            OrderedCollectionCursor.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "name": "Project A",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project B","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                            "name": "Project B",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","5"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "5")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project E","4"]'
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
def test_forward_pagination(schema: Schema, test_objects):
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
                "after": to_base64(OrderedCollectionCursor.PREFIX, '["Project B","3"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project C","2"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project D","6"]'
                    ),
                    "hasNextPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","5"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "5")),
                            "name": "Project C",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project D","6"]'
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
def test_forward_pagination_first_page(schema: Schema, test_objects):
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
                        OrderedCollectionCursor.PREFIX, '["Project A","1"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project A","1"]'
                    ),
                    "hasPreviousPage": False,
                    "hasNextPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project A","1"]'
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
def test_forward_pagination_last_page(schema: Schema, test_objects):
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
                "after": to_base64(OrderedCollectionCursor.PREFIX, '["Project D","6"]'),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project E","4"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project E","4"]'
                    ),
                    "hasNextPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project E","4"]'
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
def test_backward_pagination(schema: Schema, test_objects):
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
                "before": to_base64(
                    OrderedCollectionCursor.PREFIX, '["Project C","5"]'
                ),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project B","3"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project C","2"]'
                    ),
                    "hasPreviousPage": True,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project B","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                            "name": "Project B",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","2"]'
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
def test_backward_pagination_first_page(schema: Schema, test_objects):
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
                        OrderedCollectionCursor.PREFIX, '["Project D","6"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project E","4"]'
                    ),
                    "hasPreviousPage": True,
                    "hasNextPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project E","4"]'
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
def test_backward_pagination_last_page(schema: Schema, test_objects):
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
                "before": to_base64(
                    OrderedCollectionCursor.PREFIX, '["Project C","2"]'
                ),
            },
        )
        assert result.data == {
            "projects": {
                "pageInfo": {
                    "startCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project A","1"]'
                    ),
                    "endCursor": to_base64(
                        OrderedCollectionCursor.PREFIX, '["Project B","3"]'
                    ),
                    "hasPreviousPage": False,
                },
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project A","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                            "name": "Project A",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project B","3"]'
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
def test_cursor_pagination_custom_order(schema: Schema, test_objects):
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
                "after": to_base64(OrderedCollectionCursor.PREFIX, '["Project E","4"]'),
            },
        )
        assert result.data == {
            "projects": {
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project D","6"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "6")),
                            "name": "Project D",
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["Project C","2"]'
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
def test_cursor_pagination_joined_field_order(schema: Schema, test_objects):
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
                            OrderedCollectionCursor.PREFIX,
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
                            OrderedCollectionCursor.PREFIX,
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
                            OrderedCollectionCursor.PREFIX,
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
                            OrderedCollectionCursor.PREFIX,
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
def test_cursor_pagination_expression_order(schema: Schema, test_objects):
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
            {
                "after": to_base64(
                    OrderedCollectionCursor.PREFIX, '["209 00:00:00","4"]'
                )
            },
        )
        assert result.data == {
            "milestones": {
                "edges": [
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["212 00:00:00","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "2")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["213 00:00:00","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "1")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["213 00:00:00","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("MilestoneType", "3")),
                        },
                    },
                ]
            }
        }


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination_agg_expression_order(schema: Schema, test_objects):
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
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["2","3"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "3")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["1","1"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "1")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["1","2"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "2")),
                        },
                    },
                    {
                        "cursor": to_base64(
                            OrderedCollectionCursor.PREFIX, '["0","4"]'
                        ),
                        "node": {
                            "id": str(GlobalID("ProjectType", "4")),
                        },
                    },
                ]
            }
        }
