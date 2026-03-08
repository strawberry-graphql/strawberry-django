import pathlib

from pytest_snapshot.plugin import Snapshot

from tests.conftest import normalize_sdl

from .schema import schema

SNAPSHOTS_DIR = pathlib.Path(__file__).parent / "snapshots"


def test_schema(snapshot: Snapshot):
    snapshot.snapshot_dir = SNAPSHOTS_DIR
    snapshot.assert_match(normalize_sdl(str(schema)), "schema.gql")
