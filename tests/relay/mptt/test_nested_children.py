import pytest
import strawberry
from strawberry.relay.utils import to_base64

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from .a import MPTTAuthorConnection
from .models import MPTTAuthor


@strawberry.type
class Query:
    authors: MPTTAuthorConnection = strawberry_django.connection()


schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])


@pytest.mark.django_db(transaction=True)
def test_nested_children_total_count():
    parent = MPTTAuthor.objects.create(name="Parent")
    child1 = MPTTAuthor.objects.create(name="Child1", parent=parent)
    child2 = MPTTAuthor.objects.create(name="Child2", parent=parent)
    query = """\
    query {
      authors(first: 1) {
        totalCount
        edges {
          node {
            id
            name
            children {
              totalCount
              edges {
                node {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "authors": {
            "totalCount": 3,
            "edges": [
                {
                    "node": {
                        "id": to_base64("MPTTAuthorType", parent.pk),
                        "name": "Parent",
                        "children": {
                            "totalCount": 2,
                            "edges": [
                                {
                                    "node": {
                                        "id": to_base64("MPTTAuthorType", child1.pk),
                                        "name": "Child1",
                                    }
                                },
                                {
                                    "node": {
                                        "id": to_base64("MPTTAuthorType", child2.pk),
                                        "name": "Child2",
                                    }
                                },
                            ],
                        },
                    }
                }
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_children_total_count_no_children():
    parent = MPTTAuthor.objects.create(name="Parent")
    query = """\
    query {
      authors {
        totalCount
        edges {
          node {
            id
            name
            children {
              totalCount
              edges {
                node {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    result = schema.execute_sync(query)
    assert not result.errors
    assert result.data == {
        "authors": {
            "totalCount": 1,
            "edges": [
                {
                    "node": {
                        "id": to_base64("MPTTAuthorType", parent.pk),
                        "name": "Parent",
                        "children": {
                            "totalCount": 0,
                            "edges": [],
                        },
                    }
                }
            ],
        }
    }
