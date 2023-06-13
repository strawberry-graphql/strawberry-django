import strawberry
from strawberry import auto, relay
from strawberry.schema.config import StrawberryConfig

import strawberry_django

from .models import User


def test_relay_with_nodeid():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        id: relay.NodeID[int]
        name: auto

    @strawberry.type
    class Query:
        user: UserType

    schema = strawberry.Schema(query=Query, config=StrawberryConfig(False))
    str(schema)
    assert UserType._id_attr == "id"


def test_relay_with_resolve_id():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        name: auto

        @classmethod
        def resolve_id(cls, root):
            return root.id

    @strawberry.type
    class Query:
        user: UserType

    assert UserType._id_attr is None


def test_relay_with_resolve_id_and_node_id():
    @strawberry_django.type(User)
    class UserType(relay.Node):
        id: relay.NodeID[int]
        name: auto

        @classmethod
        def resolve_id(cls, root):
            return root.id

    @strawberry.type
    class Query:
        user: UserType

    schema = strawberry.Schema(query=Query, config=StrawberryConfig(False))
    str(schema)
    assert UserType._id_attr == "id"
