
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from strawberry.relay.utils import to_base64

from tests import utils
from tests.projects.faker import MilestoneFactory, ProjectFactory
from tests.projects.models import Milestone, Project


@pytest.mark.django_db(transaction=True)
def test_required(gql_client: utils.GraphQLTestClient):
    # Query a required field, and a nested required field with no ordering
    # We expect the queries to **not** have an `ORDER BY` clause
    query = """
      query testRequired($id: GlobalID!) {
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
      query testOptional($id: GlobalID!) {
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
                    for milestone in project.milestones.order_by("pk")],
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
