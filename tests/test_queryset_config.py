import pytest
from django.db.models import Prefetch

from strawberry_django.queryset import get_queryset_config
from tests.projects.models import Milestone, Project


def test_queryset_config_survives_filter():
    qs = Project.objects.all()
    config = get_queryset_config(qs)
    config.optimized = True
    new_qs = qs.filter(pk=1)
    assert get_queryset_config(new_qs).optimized is True


def test_queryset_config_survives_prefetch_related():
    qs = Project.objects.all()
    config = get_queryset_config(qs)
    config.optimized = True
    new_qs = qs.prefetch_related("milestones")
    assert get_queryset_config(new_qs).optimized is True


def test_queryset_config_survives_select_related():
    qs = Milestone.objects.all()
    config = get_queryset_config(qs)
    config.optimized = True
    new_qs = qs.select_related("project")
    assert get_queryset_config(new_qs).optimized is True


@pytest.mark.django_db(transaction=True)
def test_queryset_config_survives_in_prefetch_queryset():
    Project.objects.create()
    qs = Milestone.objects.all()
    config = get_queryset_config(qs)
    config.optimized = True

    project = (
        Project.objects.all()
        .prefetch_related(Prefetch("milestones", queryset=qs))
        .get()
    )

    assert get_queryset_config(project.milestones.all()).optimized is True
