import pytest
import strawberry
from strawberry import auto, relay

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

    schema = strawberry.Schema(query=Query)
    # test print_schema
    str(schema)
    # check that resolve_id_attr resolves correctly
    assert UserType.resolve_id_attr() == "id"


@pytest.mark.xfail(reason="See strawberry PR: #2844")
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

    # Crash because of early check
    schema = strawberry.Schema(query=Query)
    # test print_schema
    str(schema)


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

    schema = strawberry.Schema(query=Query)
    # test print_schema
    str(schema)
    # check that resolve_id_attr resolves correctly
    assert UserType.resolve_id_attr() == "id"
