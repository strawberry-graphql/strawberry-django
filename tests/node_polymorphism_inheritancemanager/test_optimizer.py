import pytest
from strawberry.relay import GlobalID

from .models import (
    ArtProject,
    EngineeringProject,
    ResearchProject,
    SoftwareProject,
)
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_polymorphic_mutation_abstract_model_many_to_many_rel():
    ap = ArtProject.objects.create(topic="Art", artist="Artist", art_style="Modern")
    sp = SoftwareProject.objects.create(
        topic="Software", repository="https://example.com"
    )
    ep = EngineeringProject.objects.create(
        topic="Engineering", lead_engineer="Elara Voss"
    )
    rp = ResearchProject.objects.create(
        topic="Research", supervisor="J. Hiles", research_notes="Important notes"
    )

    ap_node = GlobalID(type_name="ArtProjectType", node_id=str(ap.pk))
    sp_node = GlobalID(type_name="SoftwareProjectType", node_id=str(sp.pk))
    ep_node = GlobalID(type_name="EngineeringProjectType", node_id=str(ep.pk))
    rp_node = GlobalID(type_name="ResearchProjectType", node_id=str(rp.pk))

    query = f"""
    query {{
      node(id: "{ap_node}") {{
        __typename
        ... on ArtProjectType {{
          id
          artist
          artStyle
          dependencies {{
            totalCount
            edges {{
              node {{
                __typename
                id
              }}
            }}
          }}
          dependants {{
            totalCount
            edges {{
              node {{
                __typename
                id
              }}
            }}
          }}
        }}
      }}
    }}
    """

    mutation = f"""
    mutation {{
      updateArtProject(data: {{
        id: "{ap_node}"
        dependencies: {{ set: [ {{ id: "{sp_node}" }}, {{ id: "{ep_node}" }} ] }}
        dependants: {{ set: [ {{ id: "{rp_node}" }} ] }}
      }}) {{
        __typename
        ... on ArtProjectType {{
          id
          artist
          artStyle
          dependencies {{
            totalCount
            edges {{
              node {{
                __typename
                id
              }}
            }}
          }}
          dependants {{
            totalCount
            edges {{
              node {{
                __typename
                id
              }}
            }}
          }}
        }}
      }}
    }}
    """

    # Fetch the current project
    result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "node": {
            "__typename": "ArtProjectType",
            "id": str(ap_node),
            "artist": ap.artist,
            "artStyle": ap.art_style,
            "dependencies": {"totalCount": 0, "edges": []},
            "dependants": {"totalCount": 0, "edges": []},
        }
    }

    # Update with _new_ project dependencies
    result = schema.execute_sync(mutation)
    assert not result.errors
    assert result.data == {
        "updateArtProject": {
            "__typename": "ArtProjectType",
            "id": str(ap_node),
            "artist": ap.artist,
            "artStyle": ap.art_style,
            "dependencies": {
                "totalCount": 2,
                "edges": [
                    {"node": {"__typename": "SoftwareProjectType", "id": str(sp_node)}},
                    {
                        "node": {
                            "__typename": "EngineeringProjectType",
                            "id": str(ep_node),
                        }
                    },
                ],
            },
            "dependants": {
                "totalCount": 1,
                "edges": [
                    {"node": {"__typename": "ResearchProjectType", "id": str(rp_node)}}
                ],
            },
        }
    }

    # Update _existing_ project dependencies (no change)
    result = schema.execute_sync(mutation)
    assert not result.errors
    assert result.data == {
        "updateArtProject": {
            "__typename": "ArtProjectType",
            "id": str(ap_node),
            "artist": ap.artist,
            "artStyle": ap.art_style,
            "dependencies": {
                "totalCount": 2,  # The existing dependencies remain on the connection
                "edges": [
                    {"node": {"__typename": "SoftwareProjectType", "id": str(sp_node)}},
                    {
                        "node": {
                            "__typename": "EngineeringProjectType",
                            "id": str(ep_node),
                        }
                    },
                ],
            },
            "dependants": {
                "totalCount": 1,  # The existing dependants remain on the connection
                "edges": [
                    {"node": {"__typename": "ResearchProjectType", "id": str(rp_node)}}
                ],
            },
        }
    }
