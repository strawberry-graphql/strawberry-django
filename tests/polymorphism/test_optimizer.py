import pytest

from .models import ArtProject, ResearchProject
from .schema import schema
from ..utils import assert_num_queries


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
