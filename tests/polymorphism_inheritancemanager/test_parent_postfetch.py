import pytest

from tests.utils import assert_num_queries

from .models import ArtProject, ArtProjectNote, Company, ResearchProject
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_parent_postfetch_deep_nested_reverse_paths_baseline():
    """Parent→enfants avec reverse imbriquée sur 2 sauts.

    ArtProject -> artNotes -> details

    On vérifie que les chemins imbriqués sont préchargés sans N+1.

    Requêtes attendues (indicatif):
      1) companies
      2) projects (polymorphes)
      3) artprojectnote (IN ...)
      4) artprojectnotedetails (IN ...)
    """
    from .models import ArtProjectNoteDetails

    company = Company.objects.create(name="Cdeep0")
    ap1 = ArtProject.objects.create(company=company, topic="Art1", artist="Artist1")
    ap2 = ArtProject.objects.create(company=company, topic="Art2", artist="Artist2")
    ResearchProject.objects.create(company=company, topic="Research", supervisor="Boss")

    n11 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note1")
    n12 = ArtProjectNote.objects.create(art_project=ap1, title="A1-Note2")
    n21 = ArtProjectNote.objects.create(art_project=ap2, title="A2-Note1")

    ArtProjectNoteDetails.objects.create(art_project_note=n11, text="d11")
    ArtProjectNoteDetails.objects.create(art_project_note=n12, text="d12")
    ArtProjectNoteDetails.objects.create(art_project_note=n21, text="d21")

    query = """
    query {
      companies {
        projects {
          __typename
          ... on ArtProjectType { artNotes { details { text } } }
        }
      }
    }
    """

    with assert_num_queries(4):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data is not None
    companies = result.data["companies"]
    assert isinstance(companies, list)
    assert companies
    art_projects = [p for p in companies[0]["projects"] if p["__typename"] == "ArtProjectType"]
    details_texts = {d["text"] for p in art_projects for n in p.get("artNotes", []) for d in n.get("details", [])}
    assert {"d11", "d12", "d21"}.issubset(details_texts)
