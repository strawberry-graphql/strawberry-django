import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext

from tests.utils import assert_num_queries

from .models import (
    AndroidProject,
    ArtProject,
    Company,
    EngineeringProject,
    IOSProject,
    ResearchProject,
    SoftwareProject,
    ProjectNote,
    ArtProjectNote, ArtProjectNoteDetails, CompanyProjectLink,
)
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_polymorphic_interface_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
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

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ]
        }
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
        edges {
          node {
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
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                {
                    "node": {
                        "__typename": "SoftwareProjectType",
                        "topic": sp.topic,
                        "repository": sp.repository,
                        "timeline": sp.timeline,
                    }
                },
                {
                    "node": {
                        "__typename": "EngineeringProjectType",
                        "topic": ep.topic,
                        "leadEngineer": ep.lead_engineer,
                        "timeline": ep.timeline,
                    }
                },
            ]
        }
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
        edges {
          node {
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
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "AndroidProjectType",
                        "topic": app1.topic,
                        "repository": app1.repository,
                        "timeline": app1.timeline,
                        "androidVersion": app1.android_version,
                    }
                },
                {
                    "node": {
                        "__typename": "IOSProjectType",
                        "topic": app2.topic,
                        "repository": app2.repository,
                        "timeline": app2.timeline,
                        "iosVersion": app2.ios_version,
                    }
                },
                {
                    "node": {
                        "__typename": "EngineeringProjectType",
                        "topic": ep.topic,
                        "leadEngineer": ep.lead_engineer,
                        "timeline": ep.timeline,
                    }
                },
            ]
        }
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
        edges {
          node {
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
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "companies": {
            "edges": [
                {
                    "node": {
                        "name": company.name,
                        "mainProject": {
                            "__typename": "EngineeringProjectType",
                            "topic": ep.topic,
                            "leadEngineer": ep.lead_engineer,
                            "timeline": ep.timeline,
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_query_optimization_working():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
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

    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        result = schema.execute_sync(query)
        # validate that we're not selecting extra fields
        assert not any("research_notes" in q for q in ctx.captured_queries)
        assert not any("art_style" in q for q in ctx.captured_queries)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_paginated_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
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

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "totalCount": 2,
            "edges": [
                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_polymorphic_paginated_query_with_subtype():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note = ArtProjectNote.objects.create(art_project=ap, title="Note")


    query = """\
    query {
      projects {
        totalCount
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType {
              artist
              artNotes { edges { node { __typename title } } }
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
        "projects": {
            "totalCount": 2,
            "edges": [
                {"node": {
                    "__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist,
                    "artNotes": {"edges": [{"node": {"__typename": "ArtProjectNoteType", "title": note.title}}]}
                }},
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topic": rp.topic,
                        "supervisor": rp.supervisor,
                    }
                },
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_polymorphic_paginated_query_with_subtype_first():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note = ArtProjectNote.objects.create(art_project=ap, title="Note")


    query = """\
    query {
      projects (first: 1) {
        totalCount
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType {
              artist
              artNotes { edges { node { __typename title } } }
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
        "projects": {
            "totalCount": 2,
            "edges": [
                {"node": {
                    "__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist,
                    "artNotes": {"edges": [{"node": {"__typename": "ArtProjectNoteType", "title": note.title}}]}
                }},
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_polymorphic_paginated_query_with_subtype_last():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note = ArtProjectNote.objects.create(art_project=ap, title="Note")


    query = """\
    query {
      projects (last: 1) {
        totalCount
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType {
              artist
              artNotes { edges { node { __typename title } } }
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
        "projects": {
            "totalCount": 2,
            "edges": [
                {"node": {
                    "__typename": "ResearchProjectType",
                    "topic": rp.topic,
                    "supervisor": rp.supervisor,
                }},
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_polymorphic_offset_paginated_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        totalCount
        edges {
          node {
            __typename
            topic
            ... on ArtProjectType { artist }
            ... on ResearchProjectType { supervisor }
          }
        }
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "totalCount": 2,
            "edges": [
                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                {"node": {"__typename": "ResearchProjectType", "topic": rp.topic, "supervisor": rp.supervisor}},
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
        edges {
          node {
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
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "companies": {
            "edges": [
                {
                    "node": {
                        "name": art_company.name,
                        "mainProject": {
                            "__typename": "ArtProjectType",
                            "topic": ap.topic,
                            "artist": ap.artist,
                        },
                    }
                },
                {
                    "node": {
                        "name": research_company.name,
                        "mainProject": {
                            "__typename": "ResearchProjectType",
                            "topic": rp.topic,
                            "supervisor": rp.supervisor,
                        },
                    }
                },
            ]
        }
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
        edges {
          node {
            name
            projects {
              edges {
                node {
                  __typename
                  topic
                  ... on ArtProjectType { artist }
                  ... on ResearchProjectType { supervisor }
                }
              }
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
        "companies": {
            "edges": [
                {
                    "node": {
                        "name": "Company",
                        "projects": {
                            "edges": [
                                {"node": {"__typename": "ArtProjectType", "topic": ap.topic, "artist": ap.artist}},
                                {"node": {"__typename": "ResearchProjectType", "topic": rp.topic, "supervisor": rp.supervisor}},
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_optimizer_hints_polymorphic():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            topicUpper
            ... on ArtProjectType {
              artistUpper
              artStyleUpper
            }
          }
        }
      }
    }
    """

    with assert_num_queries(1):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "topicUpper": ap.topic.upper(),
                        "artistUpper": ap.artist.upper(),
                        "artStyleUpper": ap.art_style.upper(),
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "topicUpper": rp.topic.upper(),
                    }
                },
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_related_object_on_base():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project=ap.project_ptr, title="Note1")
    note2 = ProjectNote.objects.create(project=ap.project_ptr, title="Note2")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            notes {
              edges { node { __typename title } }
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
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "notes": {
                            "edges": [
                                {"node": {"__typename": "ProjectNoteType", "title": note1.title}},
                                {"node": {"__typename": "ProjectNoteType", "title": note2.title}},
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_more_related_object_on_base():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project=ap.project_ptr, title="Note1")
    note2 = ProjectNote.objects.create(project=ap.project_ptr, title="Note2")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note3 = ProjectNote.objects.create(project=rp.project_ptr, title="Note3")
    note4 = ProjectNote.objects.create(project=rp.project_ptr, title="Note4")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            notes { edges { node { __typename title } } }
          }
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "notes": {
                            "edges": [
                                {"node": {"__typename": "ProjectNoteType", "title": note1.title}},
                                {"node": {"__typename": "ProjectNoteType", "title": note2.title}},
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "notes": {
                            "edges": [
                                {"node": {"__typename": "ProjectNoteType", "title": note3.title}},
                                {"node": {"__typename": "ProjectNoteType", "title": note4.title}},
                            ]
                        },
                    }
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_related_object_on_subtype():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ArtProjectNote.objects.create(art_project=ap, title="Note1")
    note2 = ArtProjectNote.objects.create(art_project=ap, title="Note2")
    note3 = ArtProjectNote.objects.create(art_project=ap, title="Note3")
    note4 = ArtProjectNote.objects.create(art_project=ap, title="Note4")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            ... on ArtProjectType {
              artNotes { edges { node { __typename title } } }
            }
          }
        }
      }
    }
    """

    # j'ai mis le nombre de requette attendu a deux pour que l'on puisse visiualiser les requette en executant le test
    # avec `-vv`. Le nombre de requettes devrait etre beaucoup plus bas que les 6 que je constate actuellement.
    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {"node": {"__typename": "ArtProjectNoteType", "title": note1.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note2.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note3.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note4.title}},
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_more_related_object_on_subtype():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ArtProjectNote.objects.create(art_project=ap, title="Note1")
    note2 = ArtProjectNote.objects.create(art_project=ap, title="Note2")
    note3 = ArtProjectNote.objects.create(art_project=ap, title="Note3")
    note4 = ArtProjectNote.objects.create(art_project=ap, title="Note4")
    ap2 = ArtProject.objects.create(topic="Art2", artist="Artist2")
    note5 = ArtProjectNote.objects.create(art_project=ap2, title="Note5")
    note6 = ArtProjectNote.objects.create(art_project=ap2, title="Note6")
    ap3 = ArtProject.objects.create(topic="Art3", artist="Artist3")
    note7 = ArtProjectNote.objects.create(art_project=ap3, title="Note7")
    note8 = ArtProjectNote.objects.create(art_project=ap3, title="Note8")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            ... on ArtProjectType {
              artNotes { edges { node { __typename title } } }
            }
          }
        }
      }
    }
    """

    # j'ai mis le nombre de requette attendu a deux pour que l'on puisse visiualiser les requette en executant le test
    # avec `-vv`. Le nombre de requettes devrait etre beaucoup plus bas que les 6 que je constate actuellement.
    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {"node": {"__typename": "ArtProjectNoteType", "title": note1.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note2.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note3.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note4.title}},
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {"node": {"__typename": "ArtProjectNoteType", "title": note5.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note6.title}},
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {"node": {"__typename": "ArtProjectNoteType", "title": note7.title}},
                                {"node": {"__typename": "ArtProjectNoteType", "title": note8.title}},
                            ]
                        },
                    }
                },
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_more_related_object_on_subtype2():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ArtProjectNote.objects.create(art_project=ap, title="Note1")
    note2 = ArtProjectNote.objects.create(art_project=ap, title="Note2")
    note3 = ArtProjectNote.objects.create(art_project=ap, title="Note3")
    note4 = ArtProjectNote.objects.create(art_project=ap, title="Note4")
    ap2 = ArtProject.objects.create(topic="Art2", artist="Artist2")
    note5 = ArtProjectNote.objects.create(art_project=ap2, title="Note5")
    note6 = ArtProjectNote.objects.create(art_project=ap2, title="Note6")
    ap3 = ArtProject.objects.create(topic="Art3", artist="Artist3")
    note7 = ArtProjectNote.objects.create(art_project=ap3, title="Note7")
    note8 = ArtProjectNote.objects.create(art_project=ap3, title="Note8")

    notedetail1 = ArtProjectNoteDetails.objects.create(art_project_note=note1, text="details1")
    notedetail2 = ArtProjectNoteDetails.objects.create(art_project_note=note1, text="details2")
    notedetail3 = ArtProjectNoteDetails.objects.create(art_project_note=note1, text="details3")

    notedetail4 = ArtProjectNoteDetails.objects.create(art_project_note=note2, text="details4")
    notedetail5 = ArtProjectNoteDetails.objects.create(art_project_note=note2, text="details5")
    notedetail6 = ArtProjectNoteDetails.objects.create(art_project_note=note3, text="details6")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            ... on ArtProjectType {
              artNotes { edges { node { 
                __typename
                title
                details { edges { node { __typename text } } } 
              } } }
            }
          }
        }
      }
    }
    """

    # j'ai mis le nombre de requette attendu a deux pour que l'on puisse visiualiser les requette en executant le test
    # avec `-vv`. Le nombre de requettes devrait etre beaucoup plus bas que les 6 que je constate actuellement.
    with assert_num_queries(3):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note1.title,
                                        "details": {
                                            "edges": [
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail1.text}},
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail2.text}},
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail3.text}},
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note2.title,
                                        "details": {
                                            "edges": [
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail4.text}},
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail5.text}},
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note3.title,
                                        "details": {
                                            "edges": [
                                                {"node": {"__typename": "ArtProjectNoteDetailsType",
                                                          "text": notedetail6.text}},
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note4.title,
                                        "details": {
                                            "edges": []
                                        },
                                    }
                                },
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note5.title,
                                        "details": {
                                            "edges": []
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note6.title,
                                        "details": {
                                            "edges": []
                                        },
                                    }
                                },
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "artNotes": {
                            "edges": [
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note7.title,
                                        "details": {
                                            "edges": []
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note8.title,
                                        "details": {
                                            "edges": []
                                        },
                                    }
                                },
                            ]
                        },
                    }
                },
            ]
        }
    }

@pytest.mark.django_db(transaction=True)
def test_related_object_on_base_called_in_fragment():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project=ap.project_ptr, title="Note1")
    note2 = ProjectNote.objects.create(project=ap.project_ptr, title="Note2")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note3 = ProjectNote.objects.create(project=rp.project_ptr, title="Note3")
    note4 = ProjectNote.objects.create(project=rp.project_ptr, title="Note4")


    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            ... on ArtProjectType {
              notes { edges { node { __typename title } } }
            }
            ... on ResearchProjectType {
              notes { edges { node { __typename title } } }
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
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "notes": {
                            "edges": [
                                {"node": {"__typename": "ProjectNoteType", "title": note1.title}},
                                {"node": {"__typename": "ProjectNoteType", "title": note2.title}},
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "notes": {
                            "edges": [
                                {"node": {"__typename": "ProjectNoteType", "title": note3.title}},
                                {"node": {"__typename": "ProjectNoteType", "title": note4.title}},
                            ]
                        },
                    }
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_reverse_relation_polymorphic_resolution_on_note_project():
    """
    Couverture de la résolution polymorphe sur la relation inverse
    `ProjectNote.project` (le `project` d'une note est un `ProjectType`).

    On interroge: projects -> notes -> project { ... fragments ... }
    et on vérifie que le type concret est correctement résolu, sans N+1.
    """
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    note_a = ProjectNote.objects.create(project=ap.project_ptr, title="NoteA")
    note_r = ProjectNote.objects.create(project=rp.project_ptr, title="NoteR")

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            notes {
              edges {
                node {
                  title
                  project {
                    __typename
                    topic
                    ... on ArtProjectType { artist }
                    ... on ResearchProjectType { supervisor }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # 1 requête pour les projets, 1 pour précharger les notes et/ou la relation project
    with assert_num_queries(3):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {
        "projects": {
            "edges": [
                {
                    "node": {
                        "__typename": "ArtProjectType",
                        "notes": {
                            "edges": [
                                {
                                    "node": {
                                        "title": note_a.title,
                                        "project": {
                                            "__typename": "ArtProjectType",
                                            "topic": ap.topic,
                                            "artist": ap.artist,
                                        },
                                    }
                                }
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "__typename": "ResearchProjectType",
                        "notes": {
                            "edges": [
                                {
                                    "node": {
                                        "title": note_r.title,
                                        "project": {
                                            "__typename": "ResearchProjectType",
                                            "topic": rp.topic,
                                            "supervisor": rp.supervisor,
                                        },
                                    }
                                }
                            ]
                        },
                    }
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_reverse_relation_polymorphic_no_extra_columns_and_no_n_plus_one():
    """
    Valide l'absence de N+1 quand plusieurs notes pointent vers des projets de
    sous-types différents, et vérifie qu'aucune colonne spécifique non demandée
    n'est sélectionnée (ex.: pas de `research_notes`, pas de `art_style`).
    """
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    # Plusieurs notes pour chaque projet
    ProjectNote.objects.bulk_create(
        [
            ProjectNote(project=ap.project_ptr, title=f"A{i}") for i in range(3)
        ]
        + [
            ProjectNote(project=rp.project_ptr, title=f"R{i}") for i in range(3)
        ]
    )

    query = """\
    query {
      projects {
        edges {
          node {
            __typename
            notes {
              edges {
                node {
                  title
                  project {
                    __typename
                    topic
                    ... on ArtProjectType { artist }
                    ... on ResearchProjectType { supervisor }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # Vérifie l'absence de colonnes inutiles
    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        # Compte de requêtes constant (pas de N+1 malgré plusieurs notes)
        with assert_num_queries(3):
            result = schema.execute_sync(query)
        captured = "\n".join(q["sql"] for q in ctx.captured_queries)
        assert "research_notes" not in captured
        assert "art_style" not in captured

    assert not result.errors
    # On ne vérifie pas la forme exacte des données ici, l'objectif est
    # principalement la stabilité du nombre de requêtes et des colonnes SQL.


@pytest.mark.django_db(transaction=True)
def test_polymorphic_nested_list_with_subtype_specific_relation():
    # Dataset: one company with mixed project types; only ArtProjects have subtype-specific notes
    company = Company.objects.create(name="Company")

    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    rp = ResearchProject.objects.create(
        company=company, topic="Research", supervisor="Supervisor"
    )

    n11 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note1")
    n12 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note2")
    n21 = ArtProjectNote.objects.create(art_project=ap2, title="A2-Note1")

    query = """\
    query {
      companies {
        edges {
          node {
            name
            projects {
              edges {
                node {
                  __typename
                  ... on ArtProjectType {
                    artNotes { edges { node { title } } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # Optimisé: on évite le N+1 sur artNotes en regroupant un seul prefetch post-fetch.
    # Requêtes stables attendues:
    # 1) companies, 2) projects (polymorphes), 3) artprojectnote IN (...)
    with assert_num_queries(3):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {
        "companies": {
            "edges": [
                {
                    "node": {
                        "name": company.name,
                        "projects": {
                            "edges": [
                                {
                                    "node": {
                                        "__typename": "ArtProjectType",
                                        "artNotes": {"edges": [{"node": {"title": n11.title}}, {"node": {"title": n12.title}}]},
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectType",
                                        "artNotes": {"edges": [{"node": {"title": n21.title}}]},
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ResearchProjectType",
                                    }
                                },
                            ]
                        },
                    }
                }
            ]
        }
    }



@pytest.mark.django_db(transaction=True)
def test_inline_fragment_reverse_relation_and_fk_chain_no_n_plus_one():
    """
    Reproduit un cas proche de l'usage réel en version Relay:
    - Liste polymorphe (Company.projects) de la classe de base Project via une connection
    - Fragment inline sur le sous-type ArtProjectType pour une relation reverse (artNotes)
    - + (facultatif ici) Chaîne de FK parallèle (Company.mainProject) reliée côté ORM

    On s'attend à éviter le N+1 grâce à l'optimizer:
    - Prefetch groupé des notes d'art depuis le queryset racine (postfetch via accessor parent)

    Nombre de requêtes attendu:
      1) SELECT companies (avec potentiellement select_related(main_project))
      2) SELECT projects polymorphes pour la company
      3) SELECT artprojectnote IN (...) (prefetch groupé)
    """
    company = Company.objects.create(name="Company")

    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    rp = ResearchProject.objects.create(
        company=company, topic="Research", supervisor="Supervisor"
    )

    ArtProjectNote.objects.create(art_project=ap1, title="A1-Note1")
    ArtProjectNote.objects.create(art_project=ap1, title="A1-Note2")
    ArtProjectNote.objects.create(art_project=ap2, title="A2-Note1")

    # Lier un main_project polymorphe (FK vers Project) à la company
    company.main_project = ap1.project_ptr
    company.save(update_fields=["main_project"])

    # Une autre company pour s'assurer que la requête reste stable
    company2 = Company.objects.create(name="Company2")
    ap3 = ArtProject.objects.create(company=company2, topic="Art3", artist="Artist3")

    query = """
    query {
      companies {
        edges {
          node {
            name
            projects {
              edges {
                node {
                  __typename
                  topic
                  ... on ArtProjectType {
                    artNotes { edges { node { title } } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    with assert_num_queries(3):
        result = schema.execute_sync(query)

    assert not result.errors

    # Vérifications minimales sur la structure des données
    data = result.data["companies"]["edges"][0]["node"]
    assert data["name"] == company.name

    # Les artNotes ont été préfetchées sans N+1
    art_projects = [
        edge["node"]
        for edge in data["projects"]["edges"]
        if edge["node"]["__typename"] == "ArtProjectType"
    ]
    titles = {t["title"] for p in art_projects for t in (p.get("artNotes", {}).get("edges", [])) for t in ([t["node"]] if isinstance(t, dict) and "node" in t else [])}
    assert {"A1-Note1", "A1-Note2", "A2-Note1"}.issubset(titles)


@pytest.mark.django_db(transaction=True)
def test_optimizer_chain_company_links_to_polymorphic_project_no_n_plus_one():
    # A -> B -> polymorphic C
    # Company (A) -> CompanyProjectLink (B) -> Project (C, polymorphic via InheritanceManager)
    company = Company.objects.create(name="Company")

    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    rp1 = ResearchProject.objects.create(
        company=company, topic="Research1", supervisor="Boss1"
    )

    # Create links (B) pointing to polymorphic projects (C)
    l1 = CompanyProjectLink.objects.create(company=company, project=ap1, label="L1")
    l2 = CompanyProjectLink.objects.create(company=company, project=ap2, label="L2")
    l3 = CompanyProjectLink.objects.create(company=company, project=rp1, label="L3")

    query = """
    query {
      companies {
        edges {
          node {
        name
        projectLinks {
                  edges {
          node {
          label
          project {
            __typename
            topic
            ... on ArtProjectType { artist }
            ... on ResearchProjectType { supervisor }
          }
        }
          }}}
        }
      }
    }
    """

    # Expected stable queries (no N+1):
    # 1) companies
    # 2) companyprojectlink for those companies
    # 3) projects (polymorphic) for those links
    with assert_num_queries(3):
        result = schema.execute_sync(query)

    assert not result.errors
    data = result.data["companies"]["edges"][0]["node"]
    assert data["name"] == company.name
    # Ensure we received 3 links and correct project payloads
    links = {item["node"]["label"]: item["node"] for item in data["projectLinks"]["edges"]}

    assert links["L1"]["project"]["__typename"] == "ArtProjectType"
    assert links["L1"]["project"]["topic"] == ap1.topic
    assert links["L1"]["project"]["artist"] == ap1.artist

    assert links["L2"]["project"]["__typename"] == "ArtProjectType"
    assert links["L2"]["project"]["topic"] == ap2.topic
    assert links["L2"]["project"]["artist"] == ap2.artist

    assert links["L3"]["project"]["__typename"] == "ResearchProjectType"
    assert links["L3"]["project"]["topic"] == rp1.topic
    assert links["L3"]["project"]["supervisor"] == rp1.supervisor
