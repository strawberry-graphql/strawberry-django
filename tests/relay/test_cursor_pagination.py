from collections.abc import Iterable

import pytest
import strawberry
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import Window, F, QuerySet
from django.db.models.functions import RowNumber, Upper
from django.test.utils import CaptureQueriesContext
from strawberry.relay import Node

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import ListConnectionWithTotalCount
from strawberry_django.relay_cursor import DjangoCursorConnection
from tests.projects.models import Project


@pytest.mark.django_db(transaction=True)
def test_window_reordering():
    Project.objects.create(name="Project A")
    Project.objects.create(name="Project E")
    Project.objects.create(name="Project F")
    Project.objects.create(name="Project C")
    Project.objects.create(name="Project D")
    Project.objects.create(name="Project B")

    qs = (
        Project.objects.all()
        .order_by("name", "pk")
        .annotate(
            _row_num=Window(
                expression=RowNumber(),
                order_by=(F("name").desc(), F("pk").desc()),
            )
        )
        .filter(_row_num__lte=3)
    )
    print(list(qs.values("pk", "name", "_row_num")))
    print(str(qs.query))


@pytest.mark.django_db(transaction=True)
def test_cursor_pagination():
    Project.objects.create(name="Project A")
    Project.objects.create(name="Project E")
    Project.objects.create(name="Project F")
    Project.objects.create(name="Project C")
    Project.objects.create(name="Project D")
    Project.objects.create(name="Project B")

    @strawberry_django.type(Project)
    class ProjectType(Node):
        name: str

        @classmethod
        def get_queryset(cls, qs: QuerySet, info):
            if not qs.ordered:
                qs = qs.annotate(__foo=F("pk")).order_by(Upper("name"), "__foo")
            return qs

    @strawberry.type()
    class Query:
        projects: DjangoCursorConnection[ProjectType] = strawberry_django.connection()

        @strawberry_django.connection(DjangoCursorConnection[ProjectType])
        def projects2(self) -> Iterable[ProjectType]:
            return (
                Project.objects.all()
                .annotate(foo=Upper(F("name")))
                .order_by(F("foo").desc())
            )

        @strawberry_django.connection(ListConnectionWithTotalCount[ProjectType])
        def projects3(self) -> Iterable[ProjectType]:
            return Project.objects.all().order_by("name", "pk")

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension()])
    # b3JkZXJlZGN1cnNvcjpbIlByb2plY3QgRCIsICI1Il0=
    query = """
    query TestQuery {
        projects(after: "b3JkZXJlZGN1cnNvcjpbIlBST0pFQ1QgQSIsICIxIl0=", first: 2, last: 1) {
            edges {
                cursor
                node { id name }     
            }
            pageInfo { hasNextPage hasPreviousPage }
        }
    }
    """
    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        result = schema.execute_sync(query)
        print(ctx.captured_queries)
        print(result.data)
