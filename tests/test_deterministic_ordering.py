import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from strawberry.relay.utils import to_base64

from tests import utils
from tests.projects.faker import (
    FavoriteFactory,
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    QuizFactory,
    UserFactory,
)
from tests.projects.models import Favorite, Milestone, Project, Quiz


@pytest.mark.django_db(transaction=True)
def test_required(gql_client: utils.GraphQLTestClient):
    # Query a required field, and a nested required field with no ordering
    # We expect the queries to **not** have an `ORDER BY` clause
    query = """
      query testRequired($id: ID!) {
        projectMandatory(id: $id) {
          name
          firstMilestoneRequired {
            name
          }
        }
      }
    """

    # Sanity check the models
    assert Project._meta.ordering == []
    assert Milestone._meta.ordering == []

    # Create a project and a milestone
    project = ProjectFactory()
    milestone = MilestoneFactory(project=project)

    # Run the query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(
            query,
            variables={"id": to_base64("ProjectType", project.pk)},
        )

    # Sanity check the results
    assert not result.errors
    assert result.data == {
        "projectMandatory": {
            "name": project.name,
            "firstMilestoneRequired": {"name": milestone.name},
        }
    }

    # Assert that the queries do **not** have an `ORDER BY` clause
    for query in ctx.captured_queries:
        assert "ORDER BY" not in query["sql"]


@pytest.mark.django_db(transaction=True)
def test_optional(gql_client: utils.GraphQLTestClient):
    # Query an optional field, and a nested optional field with no ordering
    # We expect the queries to have an `ORDER BY` clause
    query = """
      query testOptional($id: ID!) {
        project(id: $id) {
          name
          firstMilestone {
            name
          }
        }
      }
    """

    # Sanity check the models
    assert Project._meta.ordering == []
    assert Milestone._meta.ordering == []

    # Create a project and a milestone
    project = ProjectFactory()
    milestone = MilestoneFactory(project=project)

    # Run the query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(
            query,
            variables={"id": to_base64("ProjectType", project.pk)},
        )

    # Sanity check the results
    assert not result.errors
    assert result.data == {
        "project": {
            "name": project.name,
            "firstMilestone": {"name": milestone.name},
        }
    }

    # Assert that the queries do have an `ORDER BY` clause
    for query in ctx.captured_queries:
        assert "ORDER BY" in query["sql"]


@pytest.mark.django_db(transaction=True)
def test_list(gql_client: utils.GraphQLTestClient):
    # Query a list field, and a nested list field with no ordering
    # We expect the queries to have an `ORDER BY` clause
    query = """
      query testList{
        projectList {
          name
          milestones {
            name
          }
        }
      }
    """

    # Sanity check the models
    assert Project._meta.ordering == []
    assert Milestone._meta.ordering == []

    # Create some projects and milestones
    projects = ProjectFactory.create_batch(3)
    milestones = []
    for project in projects:
        milestones.extend(MilestoneFactory.create_batch(3, project=project))

    # Run the query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(query)

    # Sanity check the results
    assert not result.errors
    assert result.data == {
        "projectList": [
            {
                "name": project.name,
                "milestones": [
                    {"name": milestone.name}
                    for milestone in project.milestones.order_by("pk")
                ],
            }
            for project in Project.objects.order_by("pk")
        ]
    }

    # Assert that the queries do have an `ORDER BY` clause
    for query in ctx.captured_queries:
        assert "ORDER BY" in query["sql"]


@pytest.mark.django_db(transaction=True)
def test_connection(gql_client: utils.GraphQLTestClient):
    # Query a connection field, and a nested connection field with no ordering
    # We expect the queries to have an `ORDER BY` clause
    query = """
      query testConnection{
        projectConn {
          edges {
            node {
              name
              milestoneConn {
                edges {
                  node {
                    name
                  }
                }
              }
            }
          }
        }
      }
    """

    # Sanity check the models
    assert Project._meta.ordering == []
    assert Milestone._meta.ordering == []

    # Create some projects and milestones
    projects = ProjectFactory.create_batch(3)
    milestones = []
    for project in projects:
        milestones.extend(MilestoneFactory.create_batch(3, project=project))

    # Run the query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(query)

    # Sanity check the results
    assert not result.errors
    assert result.data == {
        "projectConn": {
            "edges": [
                {
                    "node": {
                        "name": project.name,
                        "milestoneConn": {
                            "edges": [
                                {"node": {"name": milestone.name}}
                                for milestone in project.milestones.order_by("pk")
                            ]
                        },
                    }
                }
                for project in Project.objects.order_by("pk")
            ]
        }
    }

    # Assert that the queries do have an `ORDER BY` clause
    for query in ctx.captured_queries:
        assert "ORDER BY" in query["sql"]


@pytest.mark.django_db(transaction=True)
def test_paginated(gql_client: utils.GraphQLTestClient):
    # Query a paginated field, and a nested paginated field with no ordering
    # We expect the queries to have an `ORDER BY` clause
    query = """
      query testPaginated{
        projectsPaginated {
          results {
            name
            milestonesPaginated {
              results {
                name
              }
            }
          }
        }
      }
    """

    # Sanity check the models
    assert Project._meta.ordering == []
    assert Milestone._meta.ordering == []

    # Create some projects and milestones
    projects = ProjectFactory.create_batch(3)
    milestones = []
    for project in projects:
        milestones.extend(MilestoneFactory.create_batch(3, project=project))

    # Run the query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(query)

    # Sanity check the results
    assert not result.errors
    assert result.data == {
        "projectsPaginated": {
            "results": [
                {
                    "name": project.name,
                    "milestonesPaginated": {
                        "results": [
                            {"name": milestone.name}
                            for milestone in project.milestones.order_by("pk")
                        ]
                    },
                }
                for project in Project.objects.order_by("pk")
            ]
        }
    }

    # Assert that the queries do have an `ORDER BY` clause
    for query in ctx.captured_queries:
        assert "ORDER BY" in query["sql"]


@pytest.mark.django_db(transaction=True)
def test_default_ordering(gql_client: utils.GraphQLTestClient):
    # Query a field for a model with default ordering
    # We expect the default ordering to be respected
    query = """
      query testDefaultOrdering{
        favoriteConn {
          edges {
            node {
              name
            }
          }
        }
      }
    """

    # Sanity check the model
    assert Favorite._meta.ordering == ("name",)

    # Create some favorites
    # Ensure the names are in reverse order to the primary keys
    user = UserFactory()
    issue = IssueFactory()
    favorites = [
        FavoriteFactory(name=name, user=user, issue=issue) for name in ["c", "b", "a"]
    ]

    # Run the query
    # Note that we need to login to access the favorites
    with gql_client.login(user):
        result = gql_client.query(query)

    # Sanity check the results
    # We expect the favorites to be ordered by name
    assert not result.errors
    assert result.data == {
        "favoriteConn": {
            "edges": [
                {"node": {"name": favorite.name}} for favorite in reversed(favorites)
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_get_queryset_ordering(gql_client: utils.GraphQLTestClient):
    # Query a field for a type with a `get_queryset` method that applies ordering
    # We expect the ordering to be respected
    query = """
      query testGetQuerySetOrdering{
        quizList {
          title
        }
      }
    """

    # Sanity check the model
    assert Quiz._meta.ordering == []

    # Create some quizzes
    # Ensure the titles are in reverse order to the primary keys
    quizzes = [QuizFactory(title=title) for title in ["c", "b", "a"]]

    # Run the query
    result = gql_client.query(query)

    # Sanity check the results
    # We expect the quizzes to be ordered by title
    assert not result.errors
    assert result.data == {
        "quizList": [{"title": quiz.title} for quiz in reversed(quizzes)]
    }


@pytest.mark.django_db(transaction=True)
def test_graphql_ordering(gql_client: utils.GraphQLTestClient):
    # Query a field for a type that allows ordering via GraphQL
    # We expect the ordering to be respected
    query = """
      query testGraphQLOrdering{
        milestoneList(order: { name: ASC }) {
          name
        }
      }
    """

    # Sanity check the model
    assert Milestone._meta.ordering == []

    # Create some milestones
    # Ensure the names are in reverse order to the primary keys
    milestones = [MilestoneFactory(name=name) for name in ["c", "b", "a"]]

    # Run the query
    result = gql_client.query(query)

    # Sanity check the results
    # We expect the milestones to be ordered by name
    assert not result.errors
    assert result.data == {
        "milestoneList": [
            {"name": milestone.name} for milestone in reversed(milestones)
        ]
    }
