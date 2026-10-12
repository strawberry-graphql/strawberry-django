import pytest
import strawberry
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext
from strawberry import relay

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import DjangoListConnection
from tests.utils import assert_num_queries

from .models import (
    AndroidProject,
    ArtProject,
    Company,
    EngineeringProject,
    IOSProject,
    Project,
    ResearchProject,
    SoftwareProject,
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
def test_polymorphic_query_multiple_inheritance_levels():
    app1 = AndroidProject.objects.create(
        topic="Software",
        repository="https://example.com/android",
        timeline="3 months",
        android_version="14",
    )
    app2 = IOSProject.objects.create(
        topic="Software",
        repository="https://example.com/ios",
        timeline="5 months",
        ios_version="16",
    )
    ep = EngineeringProject.objects.create(
        topic="Engineering", lead_engineer="Elara Voss", timeline="6 years"
    )

    query = """\
    query {
      projects {
        __typename
        topic
        ...on TechnicalProjectType {
          timeline
        }
        ...on AppProjectType {
          repository
        }
        ...on AndroidProjectType {
          androidVersion
        }
        ...on IOSProjectType {
          iosVersion
        }
        ...on EngineeringProjectType {
          leadEngineer
        }
      }
    }
    """

    # Project Table, Content Type, AndroidProject, IOSProject, EngineeringProject = 5
    with assert_num_queries(5):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "__typename": "AndroidProjectType",
                "topic": app1.topic,
                "repository": app1.repository,
                "timeline": app1.timeline,
                "androidVersion": app1.android_version,
            },
            {
                "__typename": "IOSProjectType",
                "topic": app2.topic,
                "repository": app2.repository,
                "timeline": app2.timeline,
                "iosVersion": app2.ios_version,
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


@pytest.mark.django_db(transaction=True)
def test_optimizer_hints_polymorphic():
    ap = ArtProject.objects.create(topic="Art", artist="Artist", art_style="abstract")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        __typename
        topicUpper
        ... on ArtProjectType {
          artistUpper
          artStyleUpper
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
            {
                "__typename": "ArtProjectType",
                "topicUpper": ap.topic.upper(),
                "artistUpper": ap.artist.upper(),
                "artStyleUpper": ap.art_style.upper(),
            },
            {
                "__typename": "ResearchProjectType",
                "topicUpper": rp.topic.upper(),
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("field", ["projectsPaginated", "projectsConnection"])
def test_nested_total_count_of_subclasses(field: str):
    @strawberry_django.interface(Project)
    class ProjectType(relay.Node):
        topic: strawberry.auto

    @strawberry_django.type(ArtProject)
    class ArtProjectType(ProjectType):
        artist: strawberry.auto

    @strawberry_django.type(ResearchProject)
    class ResearchProjectType(ProjectType):
        supervisor: strawberry.auto

    @strawberry_django.type(Company)
    class CompanyType(relay.Node):
        name: strawberry.auto
        projects_paginated: OffsetPaginated[ProjectType] = (
            strawberry_django.offset_paginated(field_name="projects")
        )
        projects_connection: DjangoListConnection[ProjectType] = (
            strawberry_django.connection(field_name="projects")
        )

    @strawberry.type
    class Query:
        companies: list[CompanyType] = strawberry_django.field()

    for name in ("a", "b", "c", "d"):
        company = Company.objects.create(name=name)
        ArtProject.objects.create(company=company, topic="art", artist="Artist")
        ResearchProject.objects.create(
            company=company, topic="research", supervisor="Supervisor"
        )

    schema = strawberry.Schema(
        query=Query,
        types=[ArtProjectType, ResearchProjectType],
        extensions=[DjangoOptimizerExtension],
    )
    # The companies, their projects, and the subclass rows of each subclass, not a
    # query per company or per project
    with assert_num_queries(4):
        result = schema.execute_sync(
            f"query {{ companies {{ {field} {{ totalCount }} }} }}"
        )

    assert not result.errors
    assert result.data == {"companies": [{field: {"totalCount": 2}} for _ in range(4)]}
