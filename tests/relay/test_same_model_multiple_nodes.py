import textwrap
from typing import Optional

import pytest
import strawberry
from strawberry import relay

import strawberry_django
from tests import models

pytestmark = pytest.mark.django_db


def test_same_model_multiple_nodes():
    first_book = models.Book.objects.create(title="First Book")
    second_book = models.Book.objects.create(title="Second Book")

    @strawberry_django.type(models.Book)
    class BookA(strawberry.relay.Node):
        title: str

    @strawberry_django.type(models.Book)
    class BookB(strawberry.relay.Node):
        title: str

    @strawberry.type
    class Query:
        node: Optional[relay.Node] = strawberry_django.node()

    schema = strawberry.Schema(query=Query, types=[BookA, BookB])

    expected_schema = textwrap.dedent(
        '''
        type BookA implements Node {
          """The Globally Unique ID of this object"""
          id: GlobalID!
          title: String!
        }

        type BookB implements Node {
          """The Globally Unique ID of this object"""
          id: GlobalID!
          title: String!
        }

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
          node(
            """The ID of the object."""
            id: GlobalID!
          ): Node
        }
        '''
    ).strip()

    assert str(schema) == expected_schema

    id = relay.to_base64("BookA", first_book.pk)

    query = """
    query ($id: GlobalID!) {
      node(id: $id) {
        __typename
        ... on BookA {
          title
        }
      }
    }
    """

    result = schema.execute_sync(query, variable_values={"id": id})

    assert not result.errors

    assert result.data == {
        "node": {
            "__typename": "BookA",
            "title": "First Book",
        }
    }

    id = relay.to_base64("BookB", second_book.pk)

    query = """
    query ($id: GlobalID!) {
      node(id: $id) {
        __typename
        ... on BookB {
          title
        }
      }
    }
    """

    result = schema.execute_sync(query, variable_values={"id": id})

    assert not result.errors

    assert result.data == {
        "node": {
            "__typename": "BookB",
            "title": "Second Book",
        }
    }
