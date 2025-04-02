from collections.abc import Iterable

import pytest
import strawberry
from django.db import connections, DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext
from strawberry.relay import Node

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay_cursor import DjangoCursorConnection
from tests.projects.models import Project


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination():
    Project.objects.create(name='Project A')
    Project.objects.create(name='Project E')
    Project.objects.create(name='Project F')
    Project.objects.create(name='Project C')
    Project.objects.create(name='Project F')

    @strawberry_django.type(Project)
    class ProjectType(Node):
        name: str

        @classmethod
        def get_queryset(cls, qs, info):
            return qs.order_by('pk')

    @strawberry.type()
    class Query:
        projects: DjangoCursorConnection[ProjectType] = strawberry_django.connection()

        @strawberry_django.connection(DjangoCursorConnection[ProjectType])
        def projects2(self) -> Iterable[ProjectType]:
            return Project.objects.all().order_by('name', 'pk')

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension()])
    query = """
    query TestQuery {
        projects2 {
            __typename
            edges {
                __typename
                cursor
                node { id name }            
            }        
        }
    }
    """
    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        result = schema.execute_sync(query)
        print(ctx.captured_queries)
        print(result.data)
