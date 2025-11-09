import pytest

from tests.utils import assert_num_queries

from .models import ArtProject, ArtProjectNote, Company, ResearchProject
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_parent_postfetch_deep_nested_reverse_paths_relay():
    """
    Variante Relay (Connection) du scénario non‑Relay:
    Company -> projects (Connection) -> ArtProjectType -> artNotes (Connection) -> details (Connection)

    On vérifie que les relations inverses imbriquées sont préchargées en batch
    sur la page courante via parent_postfetch_branches, sans N+1.

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
        edges { node {
          projects {
            edges { node {
              __typename
              ... on ArtProjectType {
                artNotes { edges { node { details { edges { node { text } } } } } }
              }
            } }
          }
        } }
      }
    }
    """

    with assert_num_queries(4):
        result = schema.execute_sync(query)

    assert not result.errors
    companies = result.data["companies"]["edges"]
    assert companies and isinstance(companies, list)

    # Collect all details.text under ArtProjectType nodes
    details_texts = set()
    for c_edge in companies:
        company_node = c_edge.get("node") or {}
        projects_conn = company_node.get("projects") or {}
        for p_edge in projects_conn.get("edges", []):
            node = (p_edge or {}).get("node") or {}
            if node.get("__typename") != "ArtProjectType":
                continue
            art_notes_conn = node.get("artNotes") or {}
            for n_edge in art_notes_conn.get("edges", []):
                note_node = (n_edge or {}).get("node") or {}
                details_conn = note_node.get("details") or {}
                for d_edge in details_conn.get("edges", []):
                    d_node = (d_edge or {}).get("node") or {}
                    text = d_node.get("text")
                    if text:
                        details_texts.add(text)

    assert {"d11", "d12", "d21"}.issubset(details_texts)
