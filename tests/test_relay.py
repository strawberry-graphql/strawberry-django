import strawberry
from strawberry import auto, relay
from typing_extensions import Self

import strawberry_django

from .models import User

# textdedent not possible because of comments
expected_schema = '''
"""
The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
"""
scalar GlobalID @specifiedBy(url: "https://relay.dev/graphql/objectidentification.htm")

"""An object with a Globally Unique ID"""
interface Node {
  """The Globally Unique ID of this object"""
  id: GlobalID!
}

type Query {
  user: UserType!
}

type UserType implements Node {
  """The Globally Unique ID of this object"""
  id: GlobalID!
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
