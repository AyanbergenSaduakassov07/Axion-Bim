import pytest
from sqlalchemy import func, inspect, select

from axiom.extract import extract
from axiom.repo import tables
from axiom.repo.db import get_engine, migrate
from axiom.services import projects, revisions


@pytest.fixture
def env(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'axiom.db'}")
    migrate(engine)
    model_id = projects.create_model(engine, projects.create_project(engine, "Demo"), "Structure")
    return engine, model_id, tmp_path / "files"


def count(engine, table) -> int:
    with engine.connect() as c:
        return c.execute(select(func.count()).select_from(table)).scalar_one()


def test_migration_creates_all_tables(env):
    engine, *_ = env
    assert set(inspect(engine).get_table_names()) >= {t.name for t in tables.metadata.sorted_tables}


def test_stored_snapshot_round_trips_exactly(env, ifc_path):
    engine, model_id, files_dir = env
    path = ifc_path("weird_units")
    result = revisions.ingest(engine, model_id, path, files_dir=files_dir)
    assert result.created
    assert revisions.load_snapshot(engine, result.revision_id) == extract(path)


def test_file_is_stored_content_addressed(env, ifc_path):
    engine, model_id, files_dir = env
    result = revisions.ingest(engine, model_id, ifc_path("clean"), files_dir=files_dir)
    stored = files_dir / f"{result.file_sha256}.ifc"
    assert stored.read_bytes() == ifc_path("clean").read_bytes()


def test_reingesting_same_file_creates_no_duplicate(env, ifc_path):
    engine, model_id, files_dir = env
    first = revisions.ingest(engine, model_id, ifc_path("clean"), files_dir=files_dir)
    again = revisions.ingest(engine, model_id, ifc_path("clean"), files_dir=files_dir)
    assert (again.revision_id, again.created) == (first.revision_id, False)
    assert count(engine, tables.revisions) == 1
    assert count(engine, tables.elements) == 16


def test_revisions_are_numbered_in_ingest_order(env, ifc_path):
    engine, model_id, files_dir = env
    seqs = [
        revisions.ingest(engine, model_id, ifc_path(n), files_dir=files_dir).seq for n in ("rev1", "rev2")
    ]
    assert seqs == [1, 2]
