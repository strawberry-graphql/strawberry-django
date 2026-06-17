import asyncio
import inspect
from typing import Any, cast

import pytest
import strawberry
from asgiref.sync import sync_to_async
from strawberry import auto, relay
from typing_extensions import Self

import strawberry_django

from .models import User

# textdedent not possible because of comments
expected_schema = '''
"""An object with a Globally Unique ID"""
interface Node {
  """The Globally Unique ID of this object"""
  id: ID!
}

type Query {
  user: UserType!
}

type UserType implements Node {
  """The Globally Unique ID of this object"""
  id: ID!
  name: String!
}
'''


def test_relay_with_nodeid():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        id: relay.NodeID[int]
        name: auto

    @strawberry.type
    class Query:
        user: UserType

    schema = strawberry.Schema(query=Query)
    # test print_schema

    assert str(schema) == expected_schema.strip()
    # check that resolve_id_attr resolves correctly
    assert UserType.resolve_id_attr() == "id"


def test_relay_with_resolve_id_attr():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        name: auto

        @classmethod
        def resolve_id_attr(cls):
            return "foobar"

    @strawberry.type
    class Query:
        user: UserType

    # Crash because of early check
    schema = strawberry.Schema(query=Query)
    # test print_schema
    assert str(schema) == expected_schema.strip()


def test_relay_with_resolve_id_and_node_id():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        id: relay.NodeID[int]
        name: auto

        @classmethod
        def resolve_id(cls, root: Self, *, info):  # type: ignore
            return str(root.id)

    @strawberry.type
    class Query:
        user: UserType

    schema = strawberry.Schema(query=Query)
    # test print_schema
    assert str(schema) == expected_schema.strip()
    # check that resolve_id_attr resolves correctly
    assert UserType.resolve_id_attr() == "id"


async def test_resolve_id_is_sync_in_async_context():
    @strawberry_django.type(User)
    class DefaultPkType(relay.Node):
        name: auto

    @strawberry_django.type(User)
    class NodeIdType(relay.Node):
        id: relay.NodeID[int]
        name: auto

    # Resolving the id off an in-memory instance must not hop threads via
    # sync_to_async, even when called inside an async context.
    await asyncio.sleep(0)  # ensure a running event loop (in_async_context() is true)
    for node_type in (DefaultPkType, NodeIdType):
        result = node_type.resolve_id(cast("Any", User(pk=1)), info=cast("Any", None))
        assert result == "1"
        assert not inspect.isawaitable(result)


@pytest.mark.django_db(transaction=True)
async def test_resolve_id_deferred_field_bridges_to_sync():
    @strawberry_django.type(User)
    class NameNodeType(relay.Node):
        name: relay.NodeID[str]

    user = await sync_to_async(User.objects.create)(name="foobar")
    instance = await sync_to_async(User.objects.only("id").get)(pk=user.pk)

    # The node id field is deferred, so it is absent from __dict__ and
    # resolve_model_id must fall back to django_getattr, which bridges the
    # database read off the event loop instead of running it inline.
    result = NameNodeType.resolve_id(cast("Any", instance), info=cast("Any", None))
    assert inspect.isawaitable(result)
    assert await result == "foobar"
