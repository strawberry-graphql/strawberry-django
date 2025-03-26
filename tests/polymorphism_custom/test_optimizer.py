import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext

from tests.utils import assert_num_queries

from .models import Company, CustomPolyProject
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_query():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        __typename
        topic
        ... on ArtProjectType {
          artist
        }
        ... on ResearchProjectType {
          supervisor
        }
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist},
            {
                "__typename": "ResearchProjectType",
                "topic": rp.topic,
                "supervisor": rp.supervisor,
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_query_optimization_working():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        __typename
        topic
        ... on ArtProjectType {
          artist
        }
        ... on ResearchProjectType {
          supervisor
        }
      }
    }
    """

    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        result = schema.execute_sync(query)
        # validate that we're not selecting extra fields
        assert any("artist" in q["sql"] for q in ctx.captured_queries)
        assert not any("research_notes" in q["sql"] for q in ctx.captured_queries)
    assert not result.errors
    assert result.data == {
        "projects": [
            {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist},
            {
                "__typename": "ResearchProjectType",
                "topic": rp.topic,
                "supervisor": rp.supervisor,
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_paginated():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projectsPaginated {
        __typename
        topic
        ... on ArtProjectType {
          artist
        }
        ... on ResearchProjectType {
          supervisor
        }
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projectsPaginated": [
            {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist},
            {
                "__typename": "ResearchProjectType",
                "topic": rp.topic,
                "supervisor": rp.supervisor,
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_offset_paginated():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projectsOffsetPaginated {
        totalCount
        results {
          __typename
          topic
          ... on ArtProjectType {
            artist
          }
          ... on ResearchProjectType {
            supervisor
          }
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projectsOffsetPaginated": {
            "totalCount": 2,
            "results": [
                {
                    "__typename": "ArtProjectType",
                    "topic": ap.topic,
                    "artist": ap.artist,
                },
                {
                    "__typename": "ResearchProjectType",
                    "topic": rp.topic,
                    "supervisor": rp.supervisor,
                },
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_connection():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projectsConnection {
        totalCount
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType {
              artist
            }
            ... on ResearchProjectType {
              supervisor
            }
          }
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projectsConnection": {
            "totalCount": 2,
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "topic": ap.topic,
                        "artist": ap.artist,
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_relation():
    ap = CustomPolyProject.objects.create(topic="Art", artist="Artist")
    art_company = Company.objects.create(name="ArtCompany", main_project=ap)

    rp = CustomPolyProject.objects.create(topic="Research", supervisor="Supervisor")
    research_company = Company.objects.create(name="ResearchCompany", main_project=rp)

    query = """\
    query {
      companies {
        name
        mainProject {
            __typename
            topic
            ... on ArtProjectType {
              artist
            }
            ... on ResearchProjectType {
              supervisor
            }
          }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "companies": [
            {
                "name": art_company.name,
                "mainProject": {
                    "__typename": "ArtProjectType",
                    "topic": ap.topic,
                    "artist": ap.artist,
                },
            },
            {
                "name": research_company.name,
                "mainProject": {
                    "__typename": "ResearchProjectType",
                    "topic": rp.topic,
                    "supervisor": rp.supervisor,
                },
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_nested_list():
    company = Company.objects.create(name="Company")
    ap = CustomPolyProject.objects.create(company=company, topic="Art", artist="Artist")
    rp = CustomPolyProject.objects.create(
        company=company, topic="Research", supervisor="Supervisor"
    )

    query = """\
    query {
      companies {
        name
        projects {
            __typename
            topic
            ... on ArtProjectType {
              artist
            }
            ... on ResearchProjectType {
              supervisor
            }
          }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "companies": [
            {
                "name": "Company",
                "projects": [
                    {
                        "__typename": "ArtProjectType",
                        "topic": ap.topic,
                        "artist": ap.artist,
                    },
                    {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    },
                ],
            }
        ]
    }
