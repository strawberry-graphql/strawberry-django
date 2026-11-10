from typing import cast

import pytest
from strawberry import relay
from strawberry.types.info import Info

from strawberry_django.relay.utils import resolve_model_global_id
from tests.utils import assert_num_queries

from .models import ArtProject, Project, ResearchProject
from .schema import schema


class FakeInfo:
    schema = schema


# We only need that info contains the schema for the tests
fake_info = cast("Info", FakeInfo())


@pytest.mark.django_db(transaction=True)
def test_resolve_model_global_id():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")

    gid = relay.GlobalID(type_name="ArtProjectType", node_id=str(ap.pk))
    assert resolve_model_global_id(gid, fake_info, model=ArtProject) == ap


@pytest.mark.django_db(transaction=True)
def test_resolve_model_global_id_for_parent_model():
    ap = ArtProject.objects.create(topic="Art", artist="Artist")

    gid = relay.GlobalID(type_name="ArtProjectType", node_id=str(ap.pk))
    project = resolve_model_global_id(gid, fake_info, model=Project)
    assert isinstance(project, ArtProject)
    assert project == ap


@pytest.mark.django_db(transaction=True)
def test_resolve_model_global_id_of_another_model():
    rp = ResearchProject.objects.create(topic="Research", supervisor="Supervisor")

    gid = relay.GlobalID(type_name="ResearchProjectType", node_id=str(rp.pk))
    with (
        assert_num_queries(0),
        pytest.raises(
            ArtProject.DoesNotExist,
            match=r"^ArtProject matching query does not exist\.$",
        ),
    ):
        resolve_model_global_id(gid, fake_info, model=ArtProject)
