import pathlib

import strawberry
from pytest_snapshot.plugin import Snapshot

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .a import TreeNodeAuthorConnection, TreeNodeAuthorType
from .b import TreeNodeBookConnection, TreeNodeBookType

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_lazy_type_annotations_in_schema(snapshot: Snapshot):
    @strawberry.type
    class Query:
        books_conn: TreeNodeBookConnection = strawberry_django.connection()
        books_conn2: ListConnectionWithTotalCount[TreeNodeBookType] = (
            strawberry_django.connection()
        )
        authors_conn: TreeNodeAuthorConnection = strawberry_django.connection()
        authors_conn2: ListConnectionWithTotalCount[TreeNodeAuthorType] = (
            strawberry_django.connection()
        )

    schema = strawberry.Schema(query=Query)
    snapshot.assert_match(str(schema), "authors_and_books_schema.gql")
