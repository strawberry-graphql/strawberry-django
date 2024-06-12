import pytest
import strawberry

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from .a import AuthorConnection
from .models import RelayAuthor

pytestmark = pytest.mark.django_db


@strawberry.type
class Query:
    authors: AuthorConnection = strawberry_django.connection()


schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])


def test_nested_children_total_count():
    parent = RelayAuthor.objects.create(name="Parent")
    RelayAuthor.objects.create(name="Child", parent=parent)
    query = """
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
