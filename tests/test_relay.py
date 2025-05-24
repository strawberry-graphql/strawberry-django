import strawberry
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
