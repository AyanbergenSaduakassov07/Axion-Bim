import pytest

from axiom.repo.db import get_engine, migrate
from axiom.services import audits, projects, revisions


@pytest.fixture
def ingested(tmp_path, ifc_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'axiom.db'}")
    migrate(engine)
    model_id = projects.ensure_model(engine, "Demo", "Structure")

    def _ingest(name: str) -> int:
        return revisions.ingest(engine, model_id, ifc_path(name), files_dir=tmp_path / "files").revision_id

    return engine, _ingest


def test_audit_is_deterministic_and_round_trips(ingested):
    engine, ingest = ingested
    rev = ingest("rev3")
    first, second = audits.run_audit(engine, rev), audits.run_audit(engine, rev)
    assert first.audit_run_id != second.audit_run_id
    assert audits.load_findings(engine, first.audit_run_id) == first.findings
    assert audits.load_findings(engine, second.audit_run_id) == first.findings
    assert {(f.rule_id, f.element_name) for f in first.findings} == {("MAT-001", "C2")}


def test_reproducibility_block_is_complete(ingested):
    engine, ingest = ingested
    repro = audits.run_audit(engine, ingest("clean")).reproducibility
    assert set(repro) == {
        "file_sha256",
        "ruleset_version",
        "ids_hash",
        "engine_version",
        "scoring_config",
        "created_at",
    }
    assert len(repro["file_sha256"]) == 64 and len(repro["ruleset_version"]) == 16


def test_identity_keys_are_stable_across_revisions_of_one_model(ingested):
    engine, ingest = ingested

    def key(rev):
        return {f.identity_key for f in audits.run_audit(engine, rev).findings if f.element_name == "C2"}

    assert key(ingest("rev1")) == key(ingest("rev3"))


def test_ensure_model_is_get_or_create(ingested):
    engine, _ = ingested
    assert projects.ensure_model(engine, "Demo", "Structure") == projects.ensure_model(
        engine, "Demo", "Structure"
    )
