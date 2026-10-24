from typing import Any

import pytest
from django.db import IntegrityError, connection
from django.db.models import QuerySet
from django.test.utils import CaptureQueriesContext, isolate_apps

from strawberry_django.mutations import resolvers
from tests import models


@pytest.mark.parametrize("with_hook", [False, True])
@isolate_apps()
def test_create_inserts_prepared_instance(db, with_hook):
    events = []

    class PreparedQuerySet(QuerySet):
        def create(self, **kwargs):
            raise AssertionError("The create resolver must not call QuerySet.create")

        def insert(self, instance):
            events.append(("insert", instance))
            assert instance.pk is None
            assert instance.name == "strawberry"
            assert instance.sweetness == (8 if with_hook else 4)
            instance.save()
            return instance

    class PreparedFruit(models.Fruit):
        objects = PreparedQuerySet.as_manager()

        class Meta:
            app_label = "tests"
            proxy = True

        def clean(self):
            super().clean()
            events.append(("clean", self))
            self.name = self.name.strip().lower()
            sweetness = self.sweetness
            self.sweetness = sweetness + 1

    def pre_save_hook(instance):
        events.append(("hook", instance))
        assert instance.pk is None
        assert instance.name == " Strawberry "
        assert instance.sweetness == 3
        instance.sweetness = 7

    info: Any = None
    instance = resolvers.create(
        info,
        PreparedFruit,
        {"name": " Strawberry ", "sweetness": 3},
        pre_save_hook=pre_save_hook if with_hook else None,
    )

    assert isinstance(instance, PreparedFruit)
    assert [event for event, _ in events] == (
        ["hook", "clean", "insert"] if with_hook else ["clean", "insert"]
    )
    assert all(prepared is instance for _, prepared in events)
    saved = models.Fruit.objects.get(pk=instance.pk)
    assert saved.name == "strawberry"
    assert saved.sweetness == (8 if with_hook else 4)


@isolate_apps()
def test_create_without_insert_does_not_call_queryset_create(db):
    class CreateForbiddenQuerySet(QuerySet):
        def create(self, **kwargs):
            raise AssertionError("The create resolver must not call QuerySet.create")

    class CreateForbiddenFruit(models.Fruit):
        objects = CreateForbiddenQuerySet.as_manager()

        class Meta:
            app_label = "tests"
            proxy = True

    info: Any = None
    instance = resolvers.create(info, CreateForbiddenFruit, {"name": "strawberry"})

    assert isinstance(instance, CreateForbiddenFruit)
    assert models.Fruit.objects.get(pk=instance.pk).name == "strawberry"


def test_create_with_existing_primary_key_raises_integrity_error(db):
    existing = models.NonIdPkModel.objects.create(code="existing", text="original")
    info: Any = None

    with pytest.raises(IntegrityError):
        resolvers.create(
            info,
            models.NonIdPkModel,
            {"code": existing.pk, "text": "replacement"},
            full_clean=False,
        )

    existing.refresh_from_db()
    assert existing.text == "original"


def test_create_with_default_primary_key_does_not_issue_update(db):
    info: Any = None

    with CaptureQueriesContext(connection) as queries:
        instance = resolvers.create(info, models.UUIDModel, {"text": "created"})

    statements = [query["sql"].lstrip().upper() for query in queries]
    assert sum(statement.startswith("INSERT") for statement in statements) == 1
    assert not any(statement.startswith("UPDATE") for statement in statements)
    assert models.UUIDModel.objects.get(pk=instance.pk).text == "created"


@pytest.mark.parametrize("full_clean", [False, {"exclude": ["name"]}])
def test_create_with_full_clean_options(db, full_clean):
    info: Any = None
    instance = resolvers.create(
        info,
        models.Fruit,
        {"name": ""},
        full_clean=full_clean,
    )

    assert not instance.name
    assert not models.Fruit.objects.get(pk=instance.pk).name
