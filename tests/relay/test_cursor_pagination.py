import pytest
import strawberry
from django.db.models import QuerySet
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
    @strawberry_django.type(Project)
    class ProjectType(Node):
        name: str

        @classmethod
        def get_queryset(cls, qs: QuerySet, info):
            if not qs.ordered:
                qs = qs.order_by("name", "pk")
            return qs

    @strawberry_django.type(Milestone)
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
    Project.objects.create(id=1, name="Project A")
    Project.objects.create(id=2, name="Project C")
    Project.objects.create(id=5, name="Project C")
    Project.objects.create(id=3, name="Project B")
    Project.objects.create(id=6, name="Project D")
    Project.objects.create(id=4, name="Project E")


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
