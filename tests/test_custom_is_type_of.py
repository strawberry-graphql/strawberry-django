import typing
from typing import Any, cast

import pytest
import strawberry
from graphql import GraphQLResolveInfo
from strawberry.types.base import StrawberryObjectDefinition
from strawberry.types.cast import cast as strawberry_cast

import strawberry_django
from tests.models import Fruit


@strawberry_django.interface(Fruit)
class FruitType:
    name: str
    sweetness: int

    @classmethod
    def is_type_of(cls, obj: Any, _info: GraphQLResolveInfo) -> bool:
        if not isinstance(obj, Fruit):
            return False
        is_sweet = obj.sweetness >= 5
        return (is_sweet and cls == SweetFruitType) or (
            not is_sweet and cls == SourFruitType
        )


@strawberry_django.type(Fruit)
class SweetFruitType(FruitType):
    pass


@strawberry_django.type(Fruit)
class SourFruitType(FruitType):
    pass


@strawberry_django.interface(Fruit)
class PlainFruitType:
    name: str
    sweetness: int


@strawberry_django.type(Fruit)
class DirectSourFruitType(PlainFruitType):
    @classmethod
    def is_type_of(cls, obj: Any, _info: GraphQLResolveInfo) -> bool:
        return isinstance(obj, Fruit) and obj.sweetness < 5


class TypeOfMixin:
    @classmethod
    def is_type_of(cls, obj: Any, _info: GraphQLResolveInfo) -> bool:
        return isinstance(obj, Fruit) and obj.sweetness < 5


@strawberry_django.type(Fruit)
class MixinSourFruitType(TypeOfMixin, PlainFruitType):
    pass


@strawberry.type
class Query:
    @strawberry_django.field()
    def fruits(self) -> list[SourFruitType | SweetFruitType]:
        return typing.cast(
            "list[SourFruitType | SweetFruitType]", Fruit.objects.all().order_by("name")
        )


@pytest.fixture
def schema() -> strawberry.Schema:
    return strawberry.Schema(
        query=Query, types=(PlainFruitType, DirectSourFruitType, MixinSourFruitType)
    )


@pytest.fixture
def mock_info() -> GraphQLResolveInfo:
    return cast("GraphQLResolveInfo", object())


def test_direct_is_type_of(schema, mock_info):
    sour_fruit_type = schema.get_type_by_name("DirectSourFruitType")
    assert isinstance(sour_fruit_type, StrawberryObjectDefinition)
    assert sour_fruit_type.is_type_of is not None
    assert sour_fruit_type.is_type_of(Fruit(name="x", sweetness=0), mock_info)
    assert not sour_fruit_type.is_type_of(Fruit(name="x", sweetness=10), mock_info)


def test_mixin_is_type_of(schema, mock_info):
    sour_fruit_type = schema.get_type_by_name("MixinSourFruitType")
    assert isinstance(sour_fruit_type, StrawberryObjectDefinition)
    assert sour_fruit_type.is_type_of is not None
    assert sour_fruit_type.is_type_of(Fruit(name="x", sweetness=0), mock_info)
    assert not sour_fruit_type.is_type_of(Fruit(name="x", sweetness=10), mock_info)


def test_inherited_is_type_of(schema, mock_info):
    sour_fruit_type = schema.get_type_by_name("SourFruitType")
    assert isinstance(sour_fruit_type, StrawberryObjectDefinition)
    assert sour_fruit_type.is_type_of is not None
    assert sour_fruit_type.is_type_of(Fruit(name="x", sweetness=0), mock_info)
    assert not sour_fruit_type.is_type_of(Fruit(name="x", sweetness=10), mock_info)
    assert not sour_fruit_type.is_type_of(object(), mock_info)


def test_inherited_is_type_of_with_strawberry_type_cast(schema, mock_info):
    sour_fruit_type = schema.get_type_by_name("SourFruitType")
    sweet_fruit_type = schema.get_type_by_name("SweetFruitType")

    assert isinstance(sour_fruit_type, StrawberryObjectDefinition)
    assert isinstance(sweet_fruit_type, StrawberryObjectDefinition)
    assert sour_fruit_type.is_type_of is not None

    sweet_fruit = Fruit(name="x", sweetness=10)

    assert sour_fruit_type.is_type_of(
        strawberry_cast(SourFruitType, sweet_fruit), mock_info
    )
    assert not sour_fruit_type.is_type_of(
        strawberry_cast(SweetFruitType, Fruit(name="y", sweetness=0)),
        mock_info,
    )


@pytest.mark.django_db(transaction=True)
def test_inherited_is_type_of_with_schema(schema):
    Fruit.objects.create(name="Sour 1", sweetness=1)
    Fruit.objects.create(name="Sweet 1", sweetness=10)
    Fruit.objects.create(name="Sour 2", sweetness=2)
    Fruit.objects.create(name="Sweet 2", sweetness=8)

    result = schema.execute_sync("{ fruits { __typename ...on FruitType { name } } }")
    assert result.errors is None
    assert result.data == {
        "fruits": [
            {"__typename": "SourFruitType", "name": "Sour 1"},
            {"__typename": "SourFruitType", "name": "Sour 2"},
            {"__typename": "SweetFruitType", "name": "Sweet 1"},
            {"__typename": "SweetFruitType", "name": "Sweet 2"},
        ]
    }
