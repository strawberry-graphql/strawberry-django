import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext

from tests.utils import assert_num_queries

from .models import (
    ArtProject,
    Company,
    ResearchProject,
    SoftwareProject,
    EngineeringProject,
)
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

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

    # ContentType, base table, two subtables = 4 queries
    with assert_num_queries(4):
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
def test_polymorphic_query_abstract_model():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    sp = SoftwareProject.objects.create(
        topic="Software", repository="https://example.com", timeline="3 months"
    )
    ep = EngineeringProject.objects.create(
        topic="Engineering", lead_engineer="Elara Voss", timeline="6 years"
    )

    query = """\
    query {
      projects {
        __typename
        topic
        ... on ArtProjectType {
          artist
        }
        ...on TechnicalProjectType {
          timeline
        }
        ... on SoftwareProjectType {
          repository
        }
        ...on EngineeringProjectType {
          leadEngineer
        }
      }
    }
    """

    with assert_num_queries(5):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist},
            {
                "__typename": "SoftwareProjectType",
                "topic": sp.topic,
                "repository": sp.repository,
                "timeline": sp.timeline,
            },
            {
                "__typename": "EngineeringProjectType",
                "topic": ep.topic,
                "leadEngineer": ep.lead_engineer,
                "timeline": ep.timeline,
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_query_abstract_model_on_field():
    ep = EngineeringProject.objects.create(
        topic="Engineering", lead_engineer="Elara Voss", timeline="6 years"
    )
    company = Company.objects.create(name="Company", main_project=ep)

    query = """\
    query {
      companies {
        name
        mainProject {
            __typename
            topic
            ...on TechnicalProjectType {
              timeline
            }
            ...on EngineeringProjectType {
              leadEngineer
            }
        }
      }
    }
    """

    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "companies": [
            {
                "name": company.name,
                "mainProject": {
                    "__typename": "EngineeringProjectType",
                    "topic": ep.topic,
                    "leadEngineer": ep.lead_engineer,
                    "timeline": ep.timeline,
                },
            }
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_query_optimization_working():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

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
        assert not any("art_style" in q["sql"] for q in ctx.captured_queries)
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
def test_polymorphic_paginated_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

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

    # ContentType, base table, two subtables = 4 queries
    with assert_num_queries(4):
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
def test_polymorphic_offset_paginated_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

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

    # ContentType, base table, two subtables = 4 queries + 1 query for total count
    with assert_num_queries(5):
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
def test_polymorphic_relation():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    art_company = Company.objects.create(name="ArtCompany", main_project=ap)

    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
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

    # Company, ContentType, base table, two subtables = 5 queries
    with assert_num_queries(5):
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
    ap = ArtProject.objects.create(company=company, topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(
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

    # Company, ContentType, base table, two subtables = 5 queries
    with assert_num_queries(5):
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
