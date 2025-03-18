import pytest

from tests.utils import assert_num_queries

from .models import CustomPolyProject
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
