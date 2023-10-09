import pathlib

from pytest_snapshot.plugin import Snapshot

from .schema import schema

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_schema(snapshot: Snapshot):
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    print(schema)
    snapshot.assert_match(str(schema), "schema.gql")
