from typing import Any, cast

import pytest
from strawberry import relay
from strawberry.types.info import Info
from typing_extensions import assert_type

from .schema import Fruit, FruitModel, schema


@pytest.fixture(autouse=True)
def _fixtures(transactional_db):
    for pk, name, color in [
        (1, "Banana", "yellow"),
        (2, "Apple", "red"),
        (3, "Pineapple", "yellow"),
        (4, "Grape", "purple"),
        (5, "Orange", "orange"),
    ]:
        FruitModel.objects.create(
            id=pk,
            name=name,
            color=color,
        )


class FakeInfo:
    schema = schema


# We only need that info contains the schema for the tests
fake_info = cast("Info", FakeInfo())


@pytest.mark.parametrize("type_name", [None, 1, 1.1])
def test_global_id_wrong_type_name(type_name: Any):
    with pytest.raises(relay.GlobalIDValueError):
        relay.GlobalID(type_name=type_name, node_id="foobar")


@pytest.mark.parametrize("node_id", [None, 1, 1.1])
def test_global_id_wrong_type_node_id(node_id: Any):
    with pytest.raises(relay.GlobalIDValueError):
        relay.GlobalID(type_name="foobar", node_id=node_id)


def test_global_id_from_id():
    gid = relay.GlobalID.from_id("Zm9vYmFyOjE=")
    assert gid.type_name == "foobar"
    assert gid.node_id == "1"


@pytest.mark.parametrize("value", ["foobar", ["Zm9vYmFy"], 123])
def test_global_id_from_id_error(value: Any):
    with pytest.raises(relay.GlobalIDValueError):
        relay.GlobalID.from_id(value)


def test_global_id_resolve_type():
    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    type_ = gid.resolve_type(fake_info)
    assert type_ is Fruit


def test_global_id_resolve_node_sync():
    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = gid.resolve_node_sync(fake_info)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


def test_global_id_resolve_node_sync_non_existing():
    gid = relay.GlobalID(type_name="Fruit", node_id="999")
    fruit = gid.resolve_node_sync(fake_info)
    assert_type(fruit, relay.Node | None)
    assert fruit is None


def test_global_id_resolve_node_sync_non_existing_but_required():
    gid = relay.GlobalID(type_name="Fruit", node_id="999")
    with pytest.raises(FruitModel.DoesNotExist):
        gid.resolve_node_sync(fake_info, required=True)


def test_global_id_resolve_node_sync_ensure_type():
    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = gid.resolve_node_sync(fake_info, ensure_type=FruitModel)
    assert_type(fruit, FruitModel)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


def test_global_id_resolve_node_sync_ensure_type_with_union():
    class Foo: ...

    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = gid.resolve_node_sync(fake_info, ensure_type=FruitModel | Foo)
    assert_type(fruit, FruitModel | Foo)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


def test_global_id_resolve_node_sync_ensure_type_wrong_type():
    class Foo: ...

    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    with pytest.raises(TypeError):
        gid.resolve_node_sync(fake_info, ensure_type=Foo)


async def test_global_id_resolve_node():
    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = await gid.resolve_node(fake_info)
    assert_type(fruit, relay.Node | None)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


async def test_global_id_resolve_node_non_existing():
    gid = relay.GlobalID(type_name="Fruit", node_id="999")
    fruit = await gid.resolve_node(fake_info)
    assert_type(fruit, relay.Node | None)
    assert fruit is None


async def test_global_id_resolve_node_non_existing_but_required():
    gid = relay.GlobalID(type_name="Fruit", node_id="999")
    with pytest.raises(FruitModel.DoesNotExist):
        await gid.resolve_node(fake_info, required=True)


async def test_global_id_resolve_node_ensure_type():
    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = await gid.resolve_node(fake_info, ensure_type=FruitModel)
    assert_type(fruit, FruitModel)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


async def test_global_id_resolve_node_ensure_type_with_union():
    class Foo: ...

    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    fruit = await gid.resolve_node(fake_info, ensure_type=FruitModel | Foo)
    assert_type(fruit, FruitModel | Foo)
    assert isinstance(fruit, FruitModel)
    assert fruit.pk == 1
    assert fruit.name == "Banana"


async def test_global_id_resolve_node_ensure_type_wrong_type():
    class Foo: ...

    gid = relay.GlobalID(type_name="Fruit", node_id="1")
    with pytest.raises(TypeError):
        await gid.resolve_node(fake_info, ensure_type=Foo)
