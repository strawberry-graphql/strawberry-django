import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext

from tests.utils import assert_num_queries

from .models import (
    AndroidProject,
    ArtProject,
    ArtProjectNote,
    ArtProjectNoteDetails,
    Company,
    EngineeringProject,
    IOSProject,
    ProjectNote,
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

    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
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
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_polymorphic_query_abstract_model():
    ArtProject.objects.create(topic="Art", artist="Artist")
    sp = SoftwareProject.objects.create(
        topic="Software", repository="https://example.com", timeline="3 months"
    )
    ep = EngineeringProject.objects.create(
        topic="Engineering", lead_engineer="Elara Voss", timeline="6 years"
    )

    query = """\
    query {
      projects {
        edges { node {
          __typename
          topic
          ... on ArtProjectType { artist }
          ... on TechnicalProjectType { timeline }
          ... on SoftwareProjectType { repository }
          ... on EngineeringProjectType { leadEngineer }
        } }
      }
    }
    """

    with assert_num_queries(5):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data is not None
    # Only validate that the expected shapes are present for sp and ep
    nodes = [edge["node"] for edge in result.data["projects"]["edges"]]
    assert any(
        n["__typename"] == "SoftwareProjectType"
        and n["repository"] == sp.repository
        and n["timeline"] == sp.timeline
        for n in nodes
    )
    assert any(
        n["__typename"] == "EngineeringProjectType"
        and n["leadEngineer"] == ep.lead_engineer
        and n["timeline"] == ep.timeline
        for n in nodes
    )


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
        edges { node {
          __typename
          topic
          ...on TechnicalProjectType { timeline }
          ...on AppProjectType { repository }
          ...on AndroidProjectType { androidVersion }
          ...on IOSProjectType { iosVersion }
          ...on EngineeringProjectType { leadEngineer }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
        edges { node {
          name
          mainProject {
            __typename
            topic
            ...on TechnicalProjectType { timeline }
            ...on EngineeringProjectType { leadEngineer }
          }
        } }
      }
    }
    """

    with assert_num_queries(4):
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
        edges { node {
          __typename
          topic
          ... on ArtProjectType { artist }
          ... on ResearchProjectType { supervisor }
        } }
      }
    }
    """

    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        result = schema.execute_sync(query)
        # validate that we're not selecting extra fields
        captured = "\n".join(q["sql"] for q in ctx.captured_queries)
        assert "research_notes" not in captured
        assert "art_style" not in captured
    assert not result.errors
    assert result.data == {
        "projects": {
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
            ]
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
        edges { node {
          name
          mainProject {
            __typename
            topic
            ... on ArtProjectType { artist }
            ... on ResearchProjectType { supervisor }
          }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
        edges { node {
          name
          projects {
            edges { node {
              __typename
              topic
              ... on ArtProjectType { artist }
              ... on ResearchProjectType { supervisor }
            } }
          }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_optimizer_hints_polymorphic():
    ap = ArtProject.objects.create(topic="Art", artist="Artist", art_style="abstract")
    ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          topicUpper
          ... on ArtProjectType {
            artistUpper
            artStyleUpper
          }
        } }
      }
    }
    """

    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data is not None
    data_nodes = [e["node"] for e in result.data["projects"]["edges"]]
    # Find ArtProjectType and validate upper fields
    art = next(n for n in data_nodes if n["__typename"] == "ArtProjectType")
    assert art["topicUpper"] == ap.topic.upper()
    assert art["artistUpper"] == ap.artist.upper()
    assert art["artStyleUpper"] == ap.art_style.upper()


@pytest.mark.django_db(transaction=True)
def test_related_object_on_base():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project_id=ap.pk, title="Note1")
    note2 = ProjectNote.objects.create(project_id=ap.pk, title="Note2")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          notes { edges { node { __typename title } } }
        } }
      }
    }
    """

    with assert_num_queries(4):
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
                                        "__typename": "ProjectNoteType",
                                        "title": note1.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ProjectNoteType",
                                        "title": note2.title,
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
def test_more_related_object_on_base():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project_id=ap.pk, title="Note1")
    note2 = ProjectNote.objects.create(project_id=ap.pk, title="Note2")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note3 = ProjectNote.objects.create(project_id=rp.pk, title="Note3")
    note4 = ProjectNote.objects.create(project_id=rp.pk, title="Note4")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          notes { edges { node { __typename title } } }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
                                        "__typename": "ProjectNoteType",
                                        "title": note1.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ProjectNoteType",
                                        "title": note2.title,
                                    }
                                },
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
                                        "__typename": "ProjectNoteType",
                                        "title": note3.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ProjectNoteType",
                                        "title": note4.title,
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
def test_related_object_on_subtype():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ArtProjectNote.objects.create(art_project=ap, title="Note1")
    note2 = ArtProjectNote.objects.create(art_project=ap, title="Note2")
    note3 = ArtProjectNote.objects.create(art_project=ap, title="Note3")
    note4 = ArtProjectNote.objects.create(art_project=ap, title="Note4")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          ... on ArtProjectType {
            artNotes { edges { node { __typename title } } }
          }
        } }
      }
    }
    """

    with assert_num_queries(4):
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
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note2.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note3.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note4.title,
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
        edges { node {
          __typename
          ... on ArtProjectType {
            artNotes { edges { node { __typename title } } }
          }
        } }
      }
    }
    """

    with assert_num_queries(4):
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
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note2.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note3.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note4.title,
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
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note6.title,
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
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note8.title,
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

    notedetail1 = ArtProjectNoteDetails.objects.create(
        art_project_note=note1, text="details1"
    )
    notedetail2 = ArtProjectNoteDetails.objects.create(
        art_project_note=note1, text="details2"
    )
    notedetail3 = ArtProjectNoteDetails.objects.create(
        art_project_note=note1, text="details3"
    )

    notedetail4 = ArtProjectNoteDetails.objects.create(
        art_project_note=note2, text="details4"
    )
    notedetail5 = ArtProjectNoteDetails.objects.create(
        art_project_note=note2, text="details5"
    )
    notedetail6 = ArtProjectNoteDetails.objects.create(
        art_project_note=note3, text="details6"
    )

    query = """\
    query {
      projects {
        edges { node {
          __typename
          ... on ArtProjectType {
            artNotes { edges { node { __typename title details { edges { node { __typename text } } } } } }
          }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail1.text,
                                                    }
                                                },
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail2.text,
                                                    }
                                                },
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail3.text,
                                                    }
                                                },
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
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail4.text,
                                                    }
                                                },
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail5.text,
                                                    }
                                                },
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
                                                {
                                                    "node": {
                                                        "__typename": "ArtProjectNoteDetailsType",
                                                        "text": notedetail6.text,
                                                    }
                                                },
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note4.title,
                                        "details": {"edges": []},
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
                                        "details": {"edges": []},
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note6.title,
                                        "details": {"edges": []},
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
                                        "details": {"edges": []},
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectNoteType",
                                        "title": note8.title,
                                        "details": {"edges": []},
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
def test_reverse_relation_polymorphic_resolution_on_note_project():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    note_a = ProjectNote.objects.create(project_id=ap.pk, title="NoteA")
    note_r = ProjectNote.objects.create(project_id=rp.pk, title="NoteR")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          notes { edges { node {
            title
            project {
              __typename
              topic
              ... on ArtProjectType { artist }
              ... on ResearchProjectType { supervisor }
            }
          } } }
        } }
      }
    }
    """

    with assert_num_queries(8):
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
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    ProjectNote.objects.bulk_create(
        [ProjectNote(project_id=ap.pk, title=f"A{i}") for i in range(3)]
        + [ProjectNote(project_id=rp.pk, title=f"R{i}") for i in range(3)]
    )

    query = """\
    query {
      projects {
        edges { node {
          __typename
          notes { edges { node {
            title
            project {
              __typename
              topic
              ... on ArtProjectType { artist }
              ... on ResearchProjectType { supervisor }
            }
          } } }
        } }
      }
    }
    """

    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        with assert_num_queries(8):
            result = schema.execute_sync(query)
        captured = "\n".join(q["sql"] for q in ctx.captured_queries)
        assert "research_notes" not in captured
        assert "art_style" not in captured

    assert not result.errors


@pytest.mark.django_db(transaction=True)
def test_polymorphic_nested_list_with_subtype_specific_relation():
    company = Company.objects.create(name="Company")

    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    ResearchProject.objects.create(
        company=company, topic="Research", supervisor="Supervisor"
    )

    n11 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note1")
    n12 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note2")
    n21 = ArtProjectNote.objects.create(art_project=ap2, title="A2-Note1")

    query = """\
    query {
      companies {
        edges { node {
          name
          projects {
            edges { node {
              __typename
              ... on ArtProjectType { artNotes { edges { node { title } } } }
            } }
          }
        } }
      }
    }
    """

    with assert_num_queries(6):
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
                                        "artNotes": {
                                            "edges": [
                                                {"node": {"title": n11.title}},
                                                {"node": {"title": n12.title}},
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ArtProjectType",
                                        "artNotes": {
                                            "edges": [{"node": {"title": n21.title}}]
                                        },
                                    }
                                },
                                {"node": {"__typename": "ResearchProjectType"}},
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
def test_inline_fragment_reverse_relation_and_fk_chain_no_n_plus_one():
    company = Company.objects.create(name="Company")

    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    ResearchProject.objects.create(
        company=company, topic="Research", supervisor="Supervisor"
    )

    ArtProjectNote.objects.create(art_project=ap1, title="A1-Note1")
    ArtProjectNote.objects.create(art_project=ap1, title="A1-Note2")
    ArtProjectNote.objects.create(art_project=ap2, title="A2-Note1")

    query = """\
    query {
      companies {
        edges { node {
          name
          projects {
            edges { node {
              __typename
              topic
              ... on ArtProjectType { artNotes { edges { node { title } } } }
            } }
          }
        } }
      }
    }
    """

    with assert_num_queries(6):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data is not None
    data = result.data["companies"]["edges"][0]["node"]
    assert data["name"] == company.name
    art_projects = [
        edge["node"]
        for edge in data["projects"]["edges"]
        if edge["node"]["__typename"] == "ArtProjectType"
    ]
    titles = {
        t["node"]["title"]
        for p in art_projects
        for t in p.get("artNotes", {}).get("edges", [])
    }
    assert {"A1-Note1", "A1-Note2", "A2-Note1"}.issubset(titles)


@pytest.mark.django_db(transaction=True)
def test_polymorphic_paginated_query():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          topic
          ... on ArtProjectType { artist }
          ... on ResearchProjectType { supervisor }
        } }
      }
    }
    """

    # ContentType, base table, two subtables = 4 queries
    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
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
        edges { node {
          __typename
          topic
          ... on ArtProjectType { artist }
          ... on ResearchProjectType { supervisor }
        } }
      }
    }
    """

    # ContentType, base table, two subtables; totalCount computed via window func => 4 queries
    with assert_num_queries(4):
        result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "projects": {
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
def test_related_object_on_base_called_in_fragment():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")
    note1 = ProjectNote.objects.create(project_id=ap.pk, title="Note1")
    note2 = ProjectNote.objects.create(project_id=ap.pk, title="Note2")
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")
    note3 = ProjectNote.objects.create(project_id=rp.pk, title="Note3")
    note4 = ProjectNote.objects.create(project_id=rp.pk, title="Note4")

    query = """\
    query {
      projects {
        edges { node {
          __typename
          ... on ArtProjectType { notes { edges { node { __typename title } } } }
          ... on ResearchProjectType { notes { edges { node { __typename title } } } }
        } }
      }
    }
    """

    with assert_num_queries(5):
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
                                        "__typename": "ProjectNoteType",
                                        "title": note1.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ProjectNoteType",
                                        "title": note2.title,
                                    }
                                },
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
                                        "__typename": "ProjectNoteType",
                                        "title": note3.title,
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "ProjectNoteType",
                                        "title": note4.title,
                                    }
                                },
                            ]
                        },
                    }
                },
            ]
        }
    }
