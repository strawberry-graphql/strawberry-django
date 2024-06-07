import pathlib

import strawberry
from pytest_snapshot.plugin import Snapshot

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .a import AuthorConnection, AuthorType
from .b import BookConnection, BookType

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_lazy_type_annotations_in_schema(snapshot: Snapshot):
    @strawberry.type
    class Query:
        books_conn: BookConnection = strawberry_django.connection()
        books_conn2: ListConnectionWithTotalCount[BookType] = (
            strawberry_django.connection()
        )
        authors_conn: AuthorConnection = strawberry_django.connection()
        authors_conn2: ListConnectionWithTotalCount[AuthorType] = (
            strawberry_django.connection()
        )

    schema = strawberry.Schema(query=Query)
    snapshot.assert_match(str(schema), "authors_and_books_schema.gql")
