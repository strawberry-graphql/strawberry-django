import pytest

from strawberry_django.optimizer import OptimizerStore, OptimizerConfig
from strawberry_django.queryset import get_queryset_config
from strawberry_django.resolvers import default_qs_hook

from .models import (
    ArtProject,
    ResearchProject,
    Project,
    ArtProjectNote,
)
from .schema import schema


@pytest.mark.django_db(transaction=True)
def test_merge_postfetch_prefetch_hints_triggers_update():
    # Prepare data: one ArtProject to make sure subclass exists in results
    ap = ArtProject.objects.create(topic="Art", artist="A")
    ArtProjectNote.objects.create(art_project=ap, title="n1")

    # Start with a base queryset and pre-seed its config with a hint for the same
    # subclass model (ArtProject) but a different relation that does not exist.
    # This will exercise the update() branch instead of assignment.
    qs = Project.objects.all()
    cfg = get_queryset_config(qs)
    cfg.postfetch_prefetch[ArtProject] = {"unknown_rel"}

    # Now build a store that carries a valid postfetch hint for ArtProject.
    store = OptimizerStore()
    store.postfetch_prefetch[ArtProject] = {"art_notes"}

    # Apply the store to the queryset. We pass a dummy info since none of the
    # other optimizers run (store has no select/prefetch/only/annotate entries).
    qs2 = store.apply(qs, info=None, config=OptimizerConfig())

    # The config on the cloned queryset must contain the merged set
    merged_cfg = get_queryset_config(qs2)
    assert ArtProject in merged_cfg.postfetch_prefetch
    # Both the unknown seed and the valid art_notes must be present — this
    # validates that the update() path ran rather than replacement.
    assert merged_cfg.postfetch_prefetch[ArtProject] == {"unknown_rel", "art_notes"}


@pytest.mark.django_db(transaction=True)
def test_polymorphic_postfetch_prefetch_roots_from_strings():
    # Create one ArtProject with a related ArtProjectNote so that selecting
    # `artNotes { title }` yields a concrete root 'art_notes' coming from a
    # string prefetch path in hints generation (covers string branch).
    ap = ArtProject.objects.create(topic="Art", artist="A")
    ArtProjectNote.objects.create(art_project=ap, title="n1")

    query = """
    query {
      projects {
        edges { node {
          __typename
          ... on ArtProjectType {
            artNotes { edges { node { title } } }
          }
        } }
      }
    }
    """

    result = schema.execute_sync(query)
    assert not result.errors
    # Sanity check response shape to ensure the query actually executed paths
    # that collect subclass hints for ArtProject.
    assert any(e["node"]["__typename"] == "ArtProjectType" for e in result.data["projects"]["edges"])  # type: ignore[index]


@pytest.mark.django_db(transaction=True)
def test_postfetch_skip_when_no_instances_for_subclass():
    # Create only ResearchProject instances so that hints for ArtProject
    # (introduced by the query selection) will find no subclass instances in
    # results and hit the early `continue` branch.
    ResearchProject.objects.create(topic="R", supervisor="S")

    query = """
    query {
      projects {
        edges { node {
          __typename
          ... on ArtProjectType {
            # Requesting artNotes will generate a postfetch hint for ArtProject
            artNotes { edges { node { title } } }
          }
          ... on ResearchProjectType { supervisor }
        } }
      }
    }
    """

    result = schema.execute_sync(query)
    assert not result.errors
    # All returned items should be of ResearchProjectType
    assert all(e["node"]["__typename"] == "ResearchProjectType" for e in result.data["projects"]["edges"])  # type: ignore[index]


@pytest.mark.django_db(transaction=True)
def test_postfetch_unknown_relation_name_is_skipped():
    # Create an ArtProject but seed the queryset configuration with an unknown
    # relation name so that resolvers default_qs_hook hits the StopIteration path
    # and skips it gracefully.
    ArtProject.objects.create(topic="Art", artist="A")

    qs = Project.objects.all()
    cfg = get_queryset_config(qs)
    cfg.postfetch_prefetch[ArtProject] = {"does_not_exist"}

    # Running the hook should not raise and should not add a prefetched cache
    # entry for the unknown relation.
    qs_executed = default_qs_hook(qs)
    # Materialize and fetch the results
    objs = list(qs_executed)
    assert len(objs) >= 1
    obj = objs[0]
    cache = getattr(obj, "_prefetched_objects_cache", {})
    assert "does_not_exist" not in cache
