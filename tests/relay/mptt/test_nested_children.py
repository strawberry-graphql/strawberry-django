import pytest
import strawberry

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
    MPTTAuthor.objects.create(name="Child", parent=parent)
    query = """\
    query {
      authors(last: 1) {
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
