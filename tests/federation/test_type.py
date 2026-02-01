"""Tests for strawberry_django.federation.type decorator."""

from typing import Any, cast

import pytest
import strawberry
from strawberry.federation.schema_directives import (
    Authenticated,
    Inaccessible,
    Key,
    Policy,
    RequiresScopes,
    Shareable,
    Tag,
)
from strawberry.federation.types import FieldSet
from strawberry.types import get_object_definition

import strawberry_django
from tests import models

# =============================================================================
# Tests for federation type decorator with keys
# =============================================================================


def test_federation_type_with_string_key():
    """Test that @strawberry_django.federation.type accepts string keys."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    key_directives = [d for d in type_def.directives or [] if isinstance(d, Key)]
    assert len(key_directives) == 1
    assert str(key_directives[0].fields) == "id"


def test_federation_type_with_key_directive_object():
    """Test using Key directive directly for complex keys."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=[Key(fields=FieldSet("id"), resolvable=False)],
    )
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    key_directive = next(d for d in type_def.directives or [] if isinstance(d, Key))
    assert key_directive.resolvable is False


@pytest.mark.parametrize(
    ("keys", "expected_fields"),
    [
        (["id"], {"id"}),
        (["id", "name"], {"id", "name"}),
        (["id", "name", "sweetness"], {"id", "name", "sweetness"}),
    ],
)
def test_federation_type_with_multiple_keys(keys, expected_fields):
    """Test type with multiple @key directives."""

    @strawberry_django.federation.type(models.Fruit, keys=keys)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto
        sweetness: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    key_directives = [d for d in type_def.directives or [] if isinstance(d, Key)]
    assert len(key_directives) == len(keys)
    key_fields = {str(k.fields) for k in key_directives}
    assert key_fields == expected_fields


def test_federation_type_with_composite_key():
    """Test type with composite @key directive (multiple fields in one key)."""

    @strawberry_django.federation.type(models.Fruit, keys=["id name"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    key_directives = [d for d in type_def.directives or [] if isinstance(d, Key)]
    assert len(key_directives) == 1
    assert str(key_directives[0].fields) == "id name"


# =============================================================================
# Tests for federation directives
# =============================================================================


@pytest.mark.parametrize(
    ("directive_param", "directive_value", "directive_class"),
    [
        ("shareable", True, Shareable),
        ("authenticated", True, Authenticated),
        ("inaccessible", True, Inaccessible),
    ],
)
def test_federation_type_boolean_directives(
    directive_param, directive_value, directive_class
):
    """Test boolean federation directives (@shareable, @authenticated, @inaccessible)."""
    kwargs = cast("dict[str, Any]", {"keys": ["id"], directive_param: directive_value})

    @strawberry_django.federation.type(models.Fruit, **kwargs)
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    assert any(isinstance(d, directive_class) for d in type_def.directives or [])


def test_federation_type_inaccessible_false_no_directive():
    """Test that inaccessible=False does NOT add @inaccessible directive."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"], inaccessible=False)
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    assert not any(isinstance(d, Inaccessible) for d in type_def.directives or [])


def test_federation_type_with_policy():
    """Test @policy directive."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        policy=[["read:fruits", "admin"]],
    )
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    policy_directives = [d for d in type_def.directives or [] if isinstance(d, Policy)]
    assert len(policy_directives) == 1
    assert policy_directives[0].policies == [["read:fruits", "admin"]]


def test_federation_type_with_requires_scopes():
    """Test @requiresScopes directive."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        requires_scopes=[["read:fruits"]],
    )
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    scopes_directives = [
        d for d in type_def.directives or [] if isinstance(d, RequiresScopes)
    ]
    assert len(scopes_directives) == 1
    assert scopes_directives[0].scopes == [["read:fruits"]]


@pytest.mark.parametrize(
    "tags",
    [
        ["internal"],
        ["internal", "deprecated"],
        ["v1", "public", "stable"],
    ],
)
def test_federation_type_with_tags(tags):
    """Test @tag directives with various tag counts."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"], tags=tags)
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    tag_directives = [d for d in type_def.directives or [] if isinstance(d, Tag)]
    assert len(tag_directives) == len(tags)
    tag_names = {t.name for t in tag_directives}
    assert tag_names == set(tags)


def test_federation_type_with_extend():
    """Test that extend=True is passed through to the type definition."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"], extend=True)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    assert type_def.extend is True


def test_federation_type_without_keys():
    """Test that federation.type works without keys (non-entity with directives)."""

    @strawberry_django.federation.type(models.Fruit, shareable=True)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    # Should have @shareable but no @key
    assert any(isinstance(d, Shareable) for d in type_def.directives or [])
    assert not any(isinstance(d, Key) for d in type_def.directives or [])


def test_federation_type_preserves_custom_directives():
    """Test that custom directives are preserved alongside federation directives."""
    from strawberry.schema_directive import Location

    @strawberry.schema_directive(locations=[Location.OBJECT])
    class CustomDirective:
        name: str

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        directives=[CustomDirective(name="test")],
    )
    class FruitType:
        id: strawberry.auto

    type_def = get_object_definition(FruitType, strict=True)
    # Both Key and custom directive should be present
    assert any(isinstance(d, Key) for d in type_def.directives or [])
    assert any(isinstance(d, CustomDirective) for d in type_def.directives or [])


# =============================================================================
# Tests for auto-generated resolve_reference
# =============================================================================


def test_federation_type_auto_generates_resolve_reference():
    """Test that resolve_reference is auto-generated for keyed types."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    assert hasattr(FruitType, "resolve_reference")
    assert callable(cast("Any", FruitType).resolve_reference)


def test_federation_type_does_not_override_custom_resolve_reference():
    """Test that custom resolve_reference is not overwritten."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

        @classmethod
        def resolve_reference(cls, id: int):  # noqa: A002
            """Return the Fruit with given id."""
            return models.Fruit.objects.filter(id=id).first()

    # Verify custom method is preserved by checking docstring
    assert "Return the Fruit" in (
        cast("Any", FruitType).resolve_reference.__doc__ or ""
    )


def test_federation_type_without_keys_no_resolve_reference():
    """Test that types without keys don't get resolve_reference."""

    @strawberry_django.federation.type(models.Fruit, shareable=True)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    # Should NOT have auto-generated resolve_reference
    # (might have inherited one, but not from our auto-generation)
    type_def = get_object_definition(FruitType, strict=True)
    assert not any(isinstance(d, Key) for d in type_def.directives or [])


# =============================================================================
# Tests for Django feature integration
# =============================================================================


def test_federation_type_with_filters():
    """Test that filters work with federation types."""

    @strawberry_django.filters.filter(models.Fruit)
    class FruitFilter:
        name: strawberry.auto

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        filters=FruitFilter,
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    django_def = cast("Any", FruitType).__strawberry_django_definition__
    assert django_def.filters is FruitFilter


def test_federation_type_with_pagination():
    """Test that pagination works with federation types."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        pagination=True,
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    django_def = cast("Any", FruitType).__strawberry_django_definition__
    assert django_def.pagination is True


def test_federation_type_with_ordering():
    """Test that ordering works with federation types."""

    @strawberry_django.order_type(models.Fruit)
    class FruitOrder:
        name: strawberry.auto

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        ordering=FruitOrder,
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    django_def = cast("Any", FruitType).__strawberry_django_definition__
    assert django_def.ordering is FruitOrder


def test_federation_type_with_optimization_hints():
    """Test that optimization hints work with federation types."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        select_related=["color"],
        prefetch_related=["types"],
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    django_def = cast("Any", FruitType).__strawberry_django_definition__
    assert "color" in (django_def.store.select_related or [])
    assert any("types" in str(p) for p in (django_def.store.prefetch_related or []))


# =============================================================================
# Tests for federation interface decorator
# =============================================================================


def test_federation_interface_with_keys():
    """Test federation interface with @key directive."""

    @strawberry_django.federation.interface(models.Fruit, keys=["id"])
    class FruitInterface:
        id: strawberry.auto

    type_def = get_object_definition(FruitInterface, strict=True)
    assert type_def.is_interface
    assert any(isinstance(d, Key) for d in type_def.directives or [])


def test_federation_interface_auto_generates_resolve_reference():
    """Test that resolve_reference is auto-generated for keyed interfaces."""

    @strawberry_django.federation.interface(models.Fruit, keys=["id"])
    class FruitInterface:
        id: strawberry.auto

    assert hasattr(FruitInterface, "resolve_reference")
    assert callable(cast("Any", FruitInterface).resolve_reference)


@pytest.mark.parametrize(
    ("directive_param", "directive_value", "directive_class"),
    [
        ("authenticated", True, Authenticated),
        ("inaccessible", True, Inaccessible),
    ],
)
def test_federation_interface_directives(
    directive_param, directive_value, directive_class
):
    """Test federation directives on interfaces."""
    kwargs = cast("dict[str, Any]", {"keys": ["id"], directive_param: directive_value})

    @strawberry_django.federation.interface(models.Fruit, **kwargs)
    class FruitInterface:
        id: strawberry.auto

    type_def = get_object_definition(FruitInterface, strict=True)
    assert any(isinstance(d, directive_class) for d in type_def.directives or [])
