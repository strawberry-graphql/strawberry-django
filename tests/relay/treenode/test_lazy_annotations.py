import pathlib

import strawberry
from pytest_snapshot.plugin import Snapshot

import strawberry_django
from strawberry_django.relay import DjangoListConnection
from tests.conftest import normalize_sdl

from .a import TreeNodeAuthorConnection, TreeNodeAuthorType
from .b import TreeNodeBookConnection, TreeNodeBookType

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_lazy_type_annotations_in_schema(snapshot: Snapshot):
    @strawberry.type
    class Query:
        books_conn: TreeNodeBookConnection = strawberry_django.connection()
        books_conn2: DjangoListConnection[TreeNodeBookType] = (
            strawberry_django.connection()
        )
        authors_conn: TreeNodeAuthorConnection = strawberry_django.connection()
        authors_conn2: DjangoListConnection[TreeNodeAuthorType] = (
            strawberry_django.connection()
        )

    schema = strawberry.Schema(query=Query)
    snapshot.assert_match(normalize_sdl(str(schema)), "authors_and_books_schema.gql")
