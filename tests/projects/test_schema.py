import pathlib

from pytest_snapshot.plugin import Snapshot

from .schema import schema
from .schema_inherited import schema as schema_with_inheritance

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_schema(snapshot: Snapshot):
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    snapshot.assert_match(str(schema), "schema.gql")


def test_schema_with_inheritance(snapshot: Snapshot):
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    snapshot.assert_match(str(schema_with_inheritance), "schema_with_inheritance.gql")
