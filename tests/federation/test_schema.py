"""Tests for federation schema integration."""

import pytest
import strawberry
from strawberry.federation import Schema as FederationSchema
from strawberry.federation.schema_directives import (
    Authenticated,
    External,
    Inaccessible,
    Override,
    Policy,
    Provides,
    Requires,
    RequiresScopes,
    Shareable,
    Tag,
)
from strawberry.types import get_object_definition

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import models
from tests.utils import assert_num_queries

# =============================================================================
# Schema SDL generation
# =============================================================================


def test_schema_contains_key_directive():
    """Test that federation schema generates @key directive correctly."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(self) -> list[FruitType]:
            return []

    schema = FederationSchema(query=Query)
    sdl = str(schema)

    assert "@key" in sdl
    assert 'fields: "id"' in sdl


def test_schema_with_multiple_keys():
    """Test schema with multiple @key directives."""

    @strawberry_django.federation.type(models.Fruit, keys=["id", "name"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert sdl.count("@key") >= 2


def test_schema_with_shareable_directive():
    """Test schema with @shareable directive."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"], shareable=True)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert "@shareable" in sdl


# =============================================================================
# Federation field directives
# =============================================================================


def test_field_with_external():
    """Test @external directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(external=True)

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    assert any(isinstance(d, External) for d in name_field.directives)


def test_field_with_requires():
    """Test @requires directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(external=True)
        computed: str = strawberry_django.federation.field(
            requires=["name"],
            resolver=lambda self: f"computed-{self.name}",
        )

    type_def = get_object_definition(FruitType, strict=True)
    computed_field = next(f for f in type_def.fields if f.name == "computed")
    requires_directives = [
        d for d in computed_field.directives if isinstance(d, Requires)
    ]
    assert len(requires_directives) == 1
    assert str(requires_directives[0].fields) == "name"


def test_field_with_provides():
    """Test @provides directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry_django.federation.type(models.Color, keys=["id"])
    class ColorType:
        id: strawberry.auto
        name: strawberry.auto
        fruit: FruitType = strawberry_django.federation.field(
            provides=["name"],
        )

    type_def = get_object_definition(ColorType, strict=True)
    fruit_field = next(f for f in type_def.fields if f.name == "fruit")
    provides_directives = [d for d in fruit_field.directives if isinstance(d, Provides)]
    assert len(provides_directives) == 1
    assert str(provides_directives[0].fields) == "name"


def test_field_with_shareable():
    """Test @shareable directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(shareable=True)

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    assert any(isinstance(d, Shareable) for d in name_field.directives)


def test_field_with_authenticated():
    """Test @authenticated directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(authenticated=True)

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    assert any(isinstance(d, Authenticated) for d in name_field.directives)


def test_field_with_inaccessible():
    """Test @inaccessible directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(inaccessible=True)

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    assert any(isinstance(d, Inaccessible) for d in name_field.directives)


def test_field_with_override():
    """Test @override directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(override="products")

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    override_directive = next(
        d for d in name_field.directives if isinstance(d, Override)
    )
    assert override_directive.override_from == "products"


def test_field_with_policy():
    """Test @policy directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(
            policy=[["read:fruits", "admin"]],
        )

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    policy_directive = next(d for d in name_field.directives if isinstance(d, Policy))
    assert policy_directive.policies == [["read:fruits", "admin"]]


def test_field_with_requires_scopes():
    """Test @requiresScopes directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(
            requires_scopes=[["read:fruits"]],
        )

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    scopes_directive = next(
        d for d in name_field.directives if isinstance(d, RequiresScopes)
    )
    assert scopes_directive.scopes == [["read:fruits"]]


def test_field_with_tags():
    """Test @tag directive on field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(tags=["internal", "public"])

    type_def = get_object_definition(FruitType, strict=True)
    name_field = next(f for f in type_def.fields if f.name == "name")
    tag_directives = [d for d in name_field.directives if isinstance(d, Tag)]
    assert {t.name for t in tag_directives} == {"internal", "public"}


# =============================================================================
# _entities resolver
# =============================================================================


@pytest.mark.django_db
def test_entities_resolver_basic():
    """Test the federation _entities resolver works."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit = models.Fruit.objects.create(name="strawberry")

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
    assert result.data is not None
    assert result.data["_entities"][0]["name"] == "strawberry"


@pytest.mark.django_db
def test_entities_resolver_with_string_key():
    """Test _entities resolver with string key field."""

    @strawberry_django.federation.type(models.Fruit, keys=["name"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit = models.Fruit.objects.create(name="banana")

    result = schema.execute_sync(
        """
        query {
            _entities(representations: [{__typename: "FruitType", name: "banana"}]) {
                ... on FruitType {
                    id
                    name
                }
            }
        }
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["id"] == str(fruit.id)


@pytest.mark.django_db
def test_entities_resolver_multiple_entities():
    """Test _entities resolver with multiple entities."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit1 = models.Fruit.objects.create(name="apple")
    fruit2 = models.Fruit.objects.create(name="orange")

    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [
                {{__typename: "FruitType", id: {fruit1.id}}},
                {{__typename: "FruitType", id: {fruit2.id}}}
            ]) {{
                ... on FruitType {{
                    id
                    name
                }}
            }}
        }}
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert len(result.data["_entities"]) == 2
    names = {e["name"] for e in result.data["_entities"]}
    assert names == {"apple", "orange"}


@pytest.mark.django_db
def test_service_sdl_field():
    """Test the federation _service.sdl field."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    result = schema.execute_sync(
        """
        query {
            _service {
                sdl
            }
        }
        """
    )

    assert result.errors is None
    assert result.data is not None
    sdl = result.data["_service"]["sdl"]
    assert "@key" in sdl
    assert "FruitType" in sdl


@pytest.mark.django_db
def test_entities_resolver_with_composite_key():
    """Test _entities resolver with composite key (space-separated fields)."""

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

    models.Fruit.objects.create(name="apple", sweetness=3)

    result = schema.execute_sync(
        """
        query {
            _entities(representations: [
                {__typename: "FruitType", name: "apple", sweetness: 3}
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
    assert result.data["_entities"][0]["name"] == "apple"
    assert result.data["_entities"][0]["sweetness"] == 3


@pytest.mark.django_db
def test_entities_resolver_with_multiple_keys_uses_provided_key():
    """Test _entities with a type that has multiple @key directives."""

    @strawberry_django.federation.type(models.Fruit, keys=["id", "name"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit = models.Fruit.objects.create(name="kiwi")

    result = schema.execute_sync(
        """
        query {
            _entities(representations: [
                {__typename: "FruitType", name: "kiwi"}
            ]) {
                ... on FruitType {
                    id
                    name
                }
            }
        }
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["id"] == str(fruit.id)


@pytest.mark.django_db
def test_entities_resolver_not_found():
    """Test _entities resolver returns error for nonexistent entity."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    result = schema.execute_sync(
        """
        query {
            _entities(representations: [{__typename: "FruitType", id: 99999}]) {
                ... on FruitType {
                    id
                    name
                }
            }
        }
        """
    )

    assert result.errors is not None


@pytest.mark.django_db
def test_entities_resolver_with_fk_relationship():
    """Test _entities resolver returns related FK data."""

    @strawberry_django.federation.type(models.Color, keys=["id"])
    class ColorType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto
        color: ColorType | None

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType, ColorType])

    color = models.Color.objects.create(name="red")
    fruit = models.Fruit.objects.create(name="apple", color=color)

    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [{{__typename: "FruitType", id: {fruit.id}}}]) {{
                ... on FruitType {{
                    name
                    color {{
                        name
                    }}
                }}
            }}
        }}
        """
    )

    assert result.errors is None
    assert result.data is not None
    entity = result.data["_entities"][0]
    assert entity["name"] == "apple"
    assert entity["color"]["name"] == "red"


@pytest.mark.django_db
def test_entities_resolver_multiple_types():
    """Test _entities resolver with different entity types in one query."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry_django.federation.type(models.Color, keys=["id"])
    class ColorType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType, ColorType])

    fruit = models.Fruit.objects.create(name="grape")
    color = models.Color.objects.create(name="purple")

    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [
                {{__typename: "FruitType", id: {fruit.id}}},
                {{__typename: "ColorType", id: {color.pk}}}
            ]) {{
                ... on FruitType {{
                    name
                }}
                ... on ColorType {{
                    name
                }}
            }}
        }}
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert len(result.data["_entities"]) == 2
    names = {e["name"] for e in result.data["_entities"]}
    assert names == {"grape", "purple"}


@pytest.mark.django_db
def test_entities_resolver_with_custom_resolve_reference():
    """Test _entities calls custom resolve_reference when defined."""
    custom_called = []

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

        @classmethod
        def resolve_reference(cls, id: int, **kwargs) -> models.Fruit:  # noqa: A002
            custom_called.append(id)
            return models.Fruit.objects.get(id=id)

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])

    fruit = models.Fruit.objects.create(name="custom")

    result = schema.execute_sync(
        f"""
        query {{
            _entities(representations: [{{__typename: "FruitType", id: {fruit.id}}}]) {{
                ... on FruitType {{
                    name
                }}
            }}
        }}
        """
    )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["name"] == "custom"
    assert custom_called == [fruit.id]


@pytest.mark.django_db
def test_entities_resolver_with_optimizer():
    """Test _entities integrates with DjangoOptimizerExtension."""

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
        extensions=[DjangoOptimizerExtension()],
    )

    fruit = models.Fruit.objects.create(name="optimized")

    with assert_num_queries(1):
        result = schema.execute_sync(
            f"""
            query {{
                _entities(representations: [
                    {{__typename: "FruitType", id: {fruit.id}}}
                ]) {{
                    ... on FruitType {{
                        id
                        name
                    }}
                }}
            }}
            """
        )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["name"] == "optimized"


@pytest.mark.django_db
def test_entities_resolver_with_optimizer_and_fk():
    """Test _entities + optimizer resolves FK without N+1."""

    @strawberry_django.federation.type(models.Color, keys=["id"])
    class ColorType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto
        color: ColorType | None

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(
        query=Query,
        types=[FruitType, ColorType],
        extensions=[DjangoOptimizerExtension()],
    )

    color = models.Color.objects.create(name="yellow")
    fruit = models.Fruit.objects.create(name="banana", color=color)

    with assert_num_queries(1):
        result = schema.execute_sync(
            f"""
            query {{
                _entities(representations: [
                    {{__typename: "FruitType", id: {fruit.id}}}
                ]) {{
                    ... on FruitType {{
                        name
                        color {{
                            name
                        }}
                    }}
                }}
            }}
            """
        )

    assert result.errors is None
    assert result.data is not None
    assert result.data["_entities"][0]["color"]["name"] == "yellow"


# =============================================================================
# SDL output
# =============================================================================


def test_sdl_with_extend():
    """Test that extend=True renders in SDL."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"], extend=True)
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert "@key" in sdl


def test_sdl_with_field_directives():
    """Test that field-level directives render correctly in SDL."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(external=True)
        sweetness: strawberry.auto = strawberry_django.federation.field(shareable=True)

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert "@external" in sdl
    assert "@shareable" in sdl


def test_sdl_with_combined_type_directives():
    """Test SDL with multiple type-level directives."""

    @strawberry_django.federation.type(
        models.Fruit,
        keys=["id"],
        shareable=True,
        tags=["internal"],
    )
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert "@key" in sdl
    assert "@shareable" in sdl
    assert "@tag" in sdl


def test_sdl_composite_key_renders_correctly():
    """Test SDL renders composite key fields as single FieldSet."""

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
    sdl = str(schema)

    assert 'fields: "name sweetness"' in sdl


def test_sdl_field_requires_renders_fieldset():
    """Test that @requires renders its FieldSet in SDL."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: str = strawberry_django.federation.field(external=True)
        sweetness: strawberry.auto = strawberry_django.federation.field(
            requires=["name"],
        )

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType])
    sdl = str(schema)

    assert '@requires(fields: "name")' in sdl


def test_sdl_field_provides_renders_fieldset():
    """Test that @provides renders its FieldSet in SDL."""

    @strawberry_django.federation.type(models.Fruit, keys=["id"])
    class FruitType:
        id: strawberry.auto
        name: strawberry.auto

    @strawberry_django.federation.type(models.Color, keys=["id"])
    class ColorType:
        id: strawberry.auto
        name: strawberry.auto
        fruit: FruitType = strawberry_django.federation.field(
            provides=["name"],
        )

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

    schema = FederationSchema(query=Query, types=[FruitType, ColorType])
    sdl = str(schema)

    assert '@provides(fields: "name")' in sdl
