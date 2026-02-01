"""Tests for auto-generated resolve_reference functionality."""

import inspect
from typing import TYPE_CHECKING, Any, cast

import pytest
import strawberry
from strawberry.federation import Schema as FederationSchema
from strawberry.types.info import Info

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import models

if TYPE_CHECKING:
    from strawberry_django.utils.typing import WithStrawberryDjangoObjectDefinition


def call_resolve_reference(type_: Any, **kwargs: Any) -> Any:
    return type_.resolve_reference(**kwargs)


# =============================================================================
# Auto-generated resolve_reference
# =============================================================================


@pytest.mark.django_db
def test_resolve_reference_basic():
    """Test that auto-generated resolve_reference works."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="strawberry")

    result = call_resolve_reference(FruitType, id=fruit.id)
    assert result is not None
    assert result.name == "strawberry"


@pytest.mark.django_db
def test_resolve_reference_with_string_key():
    """Test resolve_reference with a string field as key."""

    @strawberry_django.federation.type(models.Fruit, keys=["name"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="banana")
    result = call_resolve_reference(FruitType, name="banana")
    assert result is not None
    assert result.id == fruit.id


@pytest.mark.django_db
def test_resolve_reference_with_composite_key():
    """Test resolve_reference with composite key."""

    @strawberry_django.federation.type(models.User, keys=["name group_id"])
    class UserType:
        name: strawberry.auto
        group_id: int | None

    group = models.Group.objects.create(name="test-group")
    user = models.User.objects.create(name="testuser", group=group)

    result = call_resolve_reference(UserType, name="testuser", group_id=group.pk)
    assert result is not None
    assert result.id == user.pk


@pytest.mark.django_db
def test_resolve_reference_not_found():
    """Test resolve_reference when entity doesn't exist."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    with pytest.raises(models.Fruit.DoesNotExist):
        call_resolve_reference(FruitType, id=99999)


def test_resolve_reference_accepts_info():
    """Test that resolve_reference accepts info parameter via **kwargs."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    sig = inspect.signature(cast("Any", FruitType).resolve_reference)
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


@pytest.mark.django_db
def test_custom_resolve_reference_preserved():
    """Test that custom resolve_reference is not overwritten."""
    custom_called = []

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

        @classmethod
        def resolve_reference(
            cls,
            id: int,  # noqa: A002
            info: Info | None = None,
        ) -> models.Fruit:
            custom_called.append(id)
            return models.Fruit.objects.get(id=id)

    fruit = models.Fruit.objects.create(name="custom-fruit")

    result = call_resolve_reference(FruitType, id=fruit.pk)

    assert custom_called == [fruit.id]
    assert result.name == "custom-fruit"


@pytest.mark.django_db
def test_resolve_reference_with_select_related():
    """Test that resolve_reference works with types that have optimization hints."""

    @strawberry_django.federation.type(
        models.User,
        keys=["id"],
        select_related=["group"],
    )
    class UserType:
        id: strawberry.auto
        name: strawberry.auto

    group = models.Group.objects.create(name="test-group")
    user = models.User.objects.create(name="testuser", group=group)

    result = call_resolve_reference(UserType, id=user.pk)
    assert result is not None
    assert result.name == "testuser"


@pytest.mark.django_db
def test_resolve_reference_with_multiple_keys():
    """Test type with multiple @key directives uses first key's fields."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id", "name"],
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="multi-key-fruit")

    result1 = call_resolve_reference(FruitType, id=fruit.pk)
    assert result1.name == "multi-key-fruit"

    result2 = call_resolve_reference(FruitType, name="multi-key-fruit")
    assert result2.id == fruit.id


@pytest.mark.django_db
def test_resolve_reference_uses_optimizer_extension():
    """Test resolve_reference integrates with optimizer extension."""
    optimize_calls: list[bool] = []

    class RecordingOptimizerExtension(DjangoOptimizerExtension):
        def optimize(self, qs, info, *, store=None):
            optimize_calls.append(True)
            return super().optimize(qs, info, store=store)

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(
        query=Query,
        types=[FruitType],
        extensions=[RecordingOptimizerExtension()],
    )

    fruit = models.Fruit.objects.create(name="optimized-fruit")

    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [{{__typename: "FruitType", id: {fruit.id}}}]) {{
                ... on FruitType {{
                    id
                    name
                }}
            }}
        }}
        """
    )

    assert result.errors is None
    assert optimize_calls


@pytest.mark.django_db
def test_resolve_reference_ignores_non_key_kwargs():
    """Ensure non-key kwargs in representations are ignored, not cause failure."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="extra-field-fruit")

    result = call_resolve_reference(
        FruitType,
        id=fruit.pk,
        extra="ignored",
        __typename="FruitType",
    )
    assert result is not None
    assert result.id == fruit.id
    assert result.name == "extra-field-fruit"


# =============================================================================
# resolve_model_reference function
# =============================================================================


@pytest.mark.django_db
def test_resolve_model_reference_basic():
    """Test resolve_model_reference function."""
    from strawberry_django.federation.resolve import resolve_model_reference

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="test-fruit")

    result = resolve_model_reference(
        cast("type[WithStrawberryDjangoObjectDefinition]", FruitType),
        id=fruit.pk,
    )
    assert result is not None
    assert cast("models.Fruit", result).name == "test-fruit"


@pytest.mark.django_db
def test_resolve_model_reference_with_multiple_fields():
    """Test resolve_model_reference with multiple filter fields."""
    from strawberry_django.federation.resolve import resolve_model_reference

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    fruit = models.Fruit.objects.create(name="specific-fruit")

    result = resolve_model_reference(
        cast("type[WithStrawberryDjangoObjectDefinition]", FruitType),
        id=fruit.pk,
        name="specific-fruit",
    )
    assert result is not None
    assert cast("models.Fruit", result).id == fruit.id


# =============================================================================
# get_queryset integration
# =============================================================================


@pytest.mark.django_db
def test_resolve_reference_respects_get_queryset():
    """Test that get_queryset filters are applied during resolution."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class BerryType:
        id: strawberry.auto
        name: strawberry.auto

        @classmethod
        def get_queryset(cls, queryset, info, **kwargs):
            return queryset.filter(name__contains="berry")

    models.Fruit.objects.create(name="strawberry")
    apple = models.Fruit.objects.create(name="apple")

    with pytest.raises(models.Fruit.DoesNotExist):
        call_resolve_reference(BerryType, id=apple.pk)


@pytest.mark.django_db
def test_resolve_reference_get_queryset_via_entities():
    """Test get_queryset is applied when resolving via _entities query."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class BerryType:
        id: strawberry.auto
        name: strawberry.auto

        @classmethod
        def get_queryset(cls, queryset, info, **kwargs):
            return queryset.filter(name__contains="berry")

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[BerryType])

    berry = models.Fruit.objects.create(name="strawberry")
    apple = models.Fruit.objects.create(name="apple")

    # Berry should resolve
    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [{{__typename: "BerryType", id: {berry.id}}}]) {{
                ... on BerryType {{
                    name
                }}
            }}
        }}
        """
    )
    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["name"] == "strawberry"

    # Apple should fail (filtered out by get_queryset)
    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [{{__typename: "BerryType", id: {apple.id}}}]) {{
                ... on BerryType {{
                    name
                }}
            }}
        }}
        """
    )
    assert result.errors is not None


# =============================================================================
# Edge cases
# =============================================================================


@pytest.mark.django_db
def test_resolve_reference_with_multiple_objects_returned():
    """Test MultipleObjectsReturned when key matches more than one row."""

    @strawberry_django.federation.type(models.Fruit, keys=["sweetness"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto
        sweetness: strawberry.auto

    models.Fruit.objects.create(name="apple", sweetness=5)
    models.Fruit.objects.create(name="pear", sweetness=5)

    with pytest.raises(models.Fruit.MultipleObjectsReturned):
        call_resolve_reference(FruitType, sweetness=5)


@pytest.mark.django_db
def test_resolve_reference_composite_key_via_entities():
    """Test composite key resolution end-to-end via _entities."""

    @strawberry_django.federation.type(models.Fruit, keys=["name sweetness"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto
        sweetness: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit = models.Fruit.objects.create(name="mango", sweetness=8)

    result = schema.execute_sync(
        """
        query {
            _entities(representations: [
                {__typename: "FruitType", name: "mango", sweetness: 8}
            ]) {
                ... on FruitType {
                    id
                    name
                    sweetness
                }
            }
        }
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["id"] == str(fruit.id)
    assert result.data["_entities"][0]["sweetness"] == 8
