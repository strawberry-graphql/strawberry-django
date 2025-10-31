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
    ArtProjectNote, ArtProjectNoteDetails,
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

    with assert_num_queries(1):
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

    with assert_num_queries(1):
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

    with assert_num_queries(2):
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
        assert not any("research_notes" in q for q in ctx.captured_queries)
        assert not any("art_style" in q for q in ctx.captured_queries)
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


@pytest.mark.django_db(transaction=True)
def test_optimizer_hints_polymorphic():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
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

    with assert_num_queries(1):
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
def test_related_object_on_base():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project=ap.project_ptr, title="Note1")
    note2 = ProjectNote.objects.create(project=ap.project_ptr, title="Note2")

    query = """\
    query {
      projects {
        __typename
        notes {
          __typename
          title
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "__typename": "ArtProjectType",
                "notes": [
                    {"__typename": "ProjectNoteType", "title": note1.title},
                    {"__typename": "ProjectNoteType", "title": note2.title},
                ],
            },
        ]
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
        __typename
        notes {
          __typename
          title
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "__typename": "ArtProjectType",
                "notes": [
                    {"__typename": "ProjectNoteType", "title": note1.title},
                    {"__typename": "ProjectNoteType", "title": note2.title},
                ],
            },
            {
                "__typename": "ResearchProjectType",
                "notes": [
                    {"__typename": "ProjectNoteType", "title": note3.title},
                    {"__typename": "ProjectNoteType", "title": note4.title},
                ],
            },
        ]
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
        __typename
        ... on ArtProjectType {
          artNotes {
            __typename
            title
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
        "projects": [
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {"__typename": "ArtProjectNoteType", "title": note1.title},
                    {"__typename": "ArtProjectNoteType", "title": note2.title},
                    {"__typename": "ArtProjectNoteType", "title": note3.title},
                    {"__typename": "ArtProjectNoteType", "title": note4.title},
                ],
            },
        ]
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
        __typename
        ... on ArtProjectType {
          artNotes {
            __typename
            title
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
        "projects": [
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {"__typename": "ArtProjectNoteType", "title": note1.title},
                    {"__typename": "ArtProjectNoteType", "title": note2.title},
                    {"__typename": "ArtProjectNoteType", "title": note3.title},
                    {"__typename": "ArtProjectNoteType", "title": note4.title},
                ],
            },
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {"__typename": "ArtProjectNoteType", "title": note5.title},
                    {"__typename": "ArtProjectNoteType", "title": note6.title},
                ],
            },
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {"__typename": "ArtProjectNoteType", "title": note7.title},
                    {"__typename": "ArtProjectNoteType", "title": note8.title},
                ],
            },
        ]
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
        __typename
        ... on ArtProjectType {
          artNotes {
            __typename
            title
            details {
              __typename
              text
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
        "projects": [
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note1.title,
                        "details": [
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail1.text},
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail2.text},
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail3.text},
                        ],
                    },
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note2.title,
                        "details": [
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail4.text},
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail5.text},
                        ],
                    },
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note3.title,
                        "details": [
                            {"__typename": "ArtProjectNoteDetailsType", "text": notedetail6.text},
                        ],
                    },
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note4.title,
                        "details": [],
                    },
                ],
            },
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note5.title,
                        "details": [],
                    },
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note6.title,
                        "details": [],
                    },
                ],
            },
            {
                "__typename": "ArtProjectType",
                "artNotes": [
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note7.title,
                        "details": [],
                    },
                    {
                        "__typename": "ArtProjectNoteType",
                        "title": note8.title,
                        "details": [],
                    },
                ],
            },
        ]
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
        __typename
        ... on ArtProjectType {
          notes {
            __typename
            title
          }
        }
        ... on ResearchProjectType {
          notes {
            __typename
            title
          }
        }
      }
    }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "__typename": "ArtProjectType",
                "notes": [
                    {"__typename": "ProjectNoteType", "title": note1.title},
                    {"__typename": "ProjectNoteType", "title": note2.title},
                ],
            },
            {
                "__typename": "ResearchProjectType",
                "notes": [
                    {"__typename": "ProjectNoteType", "title": note3.title},
                    {"__typename": "ProjectNoteType", "title": note4.title},
                ],
            },
        ]
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
        __typename
        notes {
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
    """

    # 1 requête pour les projets, 1 pour précharger les notes et/ou la relation project
    with assert_num_queries(3):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "__typename": "ArtProjectType",
                "notes": [
                    {
                        "title": note_a.title,
                        "project": {
                            "__typename": "ArtProjectType",
                            "topic": ap.topic,
                            "artist": ap.artist,
                        },
                    }
                ],
            },
            {
                "__typename": "ResearchProjectType",
                "notes": [
                    {
                        "title": note_r.title,
                        "project": {
                            "__typename": "ResearchProjectType",
                            "topic": rp.topic,
                            "supervisor": rp.supervisor,
                        },
                    }
                ],
            },
        ]
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
        __typename
        notes {
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
        name
        projects {
          __typename
          ... on ArtProjectType {
            artNotes { title }
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
        "companies": [
            {
                "name": company.name,
                "projects": [
                    {
                        "__typename": "ArtProjectType",
                        "artNotes": [
                            {"title": n11.title},
                            {"title": n12.title},
                        ],
                    },
                    {
                        "__typename": "ArtProjectType",
                        "artNotes": [
                            {"title": n21.title},
                        ],
                    },
                    {
                        "__typename": "ResearchProjectType",
                    },
                ],
            }
        ]
    }
