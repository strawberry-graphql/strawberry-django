from collections.abc import Iterable
from typing import Any

import pytest
import strawberry
from django.db import connections
from django.test.utils import CaptureQueriesContext
from strawberry import Info, auto, relay

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoListConnection
from tests.models import Group, Tag, User


@strawberry_django.type(Tag)
class TagType(relay.Node):
    name: auto


@strawberry_django.type(Group)
class GroupType(relay.Node):
    name: auto
    tags: list[TagType]


@strawberry_django.type(User)
class UserType(relay.Node):
    name: auto
    group: GroupType


@strawberry.type()
class CustomConnection(relay.Connection[UserType]):
    @classmethod
    def resolve_connection(
        cls,
        nodes,
        *,
        info: Info,
        before: str | None = None,
        after: str | None = None,
        first: int | None = None,
        last: int | None = None,
        **kwargs: Any,
    ):
        # Delegate to DjangoListConnection for the actual resolution
        # This mimics what users do when creating custom connections
        return DjangoListConnection[UserType].resolve_connection(
            nodes=nodes,
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
        )


@strawberry.type
class Query:
    @strawberry_django.connection(
        graphql_type=CustomConnection,
    )
    def users(self, info: Info) -> Iterable[User]:
        return User.objects.all()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("enable_only_optimization", [True, False])
def test_fragment_with_standard_connection_no_n1(enable_only_optimization: bool):
    """Test that fragments with standard DjangoListConnection work properly (baseline)."""
    # Setup test data with nested relationships
    tag1 = Tag.objects.create(name="tag1")
    tag2 = Tag.objects.create(name="tag2")
    tag3 = Tag.objects.create(name="tag3")

    group1 = Group.objects.create(name="group1")
    group1.tags.add(tag1, tag2)

    group2 = Group.objects.create(name="group2")
    group2.tags.add(tag3)

    User.objects.create(name="user1", group=group1)
    User.objects.create(name="user2", group=group2)
    User.objects.create(name="user3", group=group1)

    # Create schema with standard DjangoListConnection (not custom)
    @strawberry.type
    class StandardQuery:
        users: DjangoListConnection[UserType] = strawberry_django.connection()

    standard_schema = strawberry.Schema(
        query=StandardQuery,
        extensions=[
            DjangoOptimizerExtension(enable_only_optimization=enable_only_optimization)
        ],
    )

    query = """
        query MyQuery {
          users {
            edges {
              node {
                name
                group {
                  name
                }
              }
              ...UserFragment
            }
          }
        }

        fragment UserFragment on UserTypeEdge {
          node {
            name
            group {
              name
              tags {
                name
              }
            }
          }
        }
    """

    with CaptureQueriesContext(connections["default"]) as captured:
        result = standard_schema.execute_sync(query)

    # With standard connection, this should work properly (baseline test)
    assert len(captured) <= 3, (
        f"Standard connection should have at most 3 queries, but got {len(captured)}."
    )

    assert result.errors is None
    assert result.data is not None
    assert result.data == {
        "users": {
            "edges": [
                {
                    "node": {
                        "name": "user1",
                        "group": {
                            "name": "group1",
                            "tags": [{"name": "tag1"}, {"name": "tag2"}],
                        },
                    }
                },
                {
                    "node": {
                        "name": "user2",
                        "group": {"name": "group2", "tags": [{"name": "tag3"}]},
                    }
                },
                {
                    "node": {
                        "name": "user3",
                        "group": {
                            "name": "group1",
                            "tags": [{"name": "tag1"}, {"name": "tag2"}],
                        },
                    }
                },
            ]
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("enable_only_optimization", [True, False])
def test_fragment_with_custom_connection_no_n1(enable_only_optimization: bool):
    """Test that fragments with custom connections don't cause N+1 queries."""
    # Setup test data with nested relationships
    tag1 = Tag.objects.create(name="tag1")
    tag2 = Tag.objects.create(name="tag2")
    tag3 = Tag.objects.create(name="tag3")

    group1 = Group.objects.create(name="group1")
    group1.tags.add(tag1, tag2)

    group2 = Group.objects.create(name="group2")
    group2.tags.add(tag3)

    User.objects.create(name="user1", group=group1)
    User.objects.create(name="user2", group=group2)
    User.objects.create(name="user3", group=group1)

    schema = strawberry.Schema(
        query=Query,
        extensions=[
            DjangoOptimizerExtension(enable_only_optimization=enable_only_optimization)
        ],
    )

    # Query that uses a fragment selecting deeper relationships than the main query
    query = """
        query MyQuery {
          users {
            edges {
              node {
                name
                group {
                  name
                }
              }
              ...UserFragment
            }
          }
        }

        fragment UserFragment on UserTypeEdge {
          node {
            name
            group {
              name
              tags {
                name
              }
            }
          }
        }
    """

    with CaptureQueriesContext(connections["default"]) as captured:
        result = schema.execute_sync(query)

    assert len(captured) <= 3, (
        f"Expected at most 3 queries, but got {len(captured)}. "
        "This indicates an N+1 query issue. The tags should be prefetched in a single query."
    )

    assert result.errors is None
    assert result.data is not None

    assert result.data == {
        "users": {
            "edges": [
                {
                    "node": {
                        "name": "user1",
                        "group": {
                            "name": "group1",
                            "tags": [{"name": "tag1"}, {"name": "tag2"}],
                        },
                    }
                },
                {
                    "node": {
                        "name": "user2",
                        "group": {"name": "group2", "tags": [{"name": "tag3"}]},
                    }
                },
                {
                    "node": {
                        "name": "user3",
                        "group": {
                            "name": "group1",
                            "tags": [{"name": "tag1"}, {"name": "tag2"}],
                        },
                    }
                },
            ]
        }
    }
