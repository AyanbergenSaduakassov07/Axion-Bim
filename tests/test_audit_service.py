import pytest

from axiom.repo.db import get_engine, migrate
from axiom.services import audits, projects, quantities, revisions


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
        "geometry",
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


def test_audit_with_ids_merges_findings_and_records_hash(ingested, tmp_path):
    from tests.test_ids import STRUCTURAL  # noqa: PLC0415

    engine, ingest = ingested
    result = audits.run_audit(
        engine, ingest("missing_props"), ids_path=STRUCTURAL, files_dir=tmp_path / "files"
    )
    ids_hash = result.reproducibility["ids_hash"]
    assert len(ids_hash) == 64
    assert (tmp_path / "files" / f"{ids_hash}.ids").read_bytes() == STRUCTURAL.read_bytes()
    walls = sorted(f.element_name for f in result.findings if f.rule_id == "IDS:STR-WALL")
    assert walls == ["W1", "W2", "W3"]
    assert {"GEO-001", "IDS:STR-WALL"} <= set(result.counts)
    assert audits.load_findings(engine, result.audit_run_id) == result.findings


def test_clean_model_scores_100_and_persists_scoring_config(ingested):
    engine, ingest = ingested
    result = audits.run_audit(engine, ingest("clean"))
    assert result.mhi.score == 100 and result.mhi.coverage == 100 and not result.mhi.blocked
    assert result.mhi.dimensions["ids_compliance"].score is None  # no IDS given: flagged, not scored
    assert result.reproducibility["scoring_config"] == result.mhi.config_version
    stored = audits.load_audit_summary(engine, result.audit_run_id)
    assert stored["mhi"]["score"] == 100 and stored["scoring_config"]["version"] == result.mhi.config_version


def test_duplicate_guid_blocks_the_model(ingested):
    engine, ingest = ingested
    mhi = audits.run_audit(engine, ingest("duplicate_guid")).mhi
    assert mhi.blocked and len(mhi.blocking) == 1


def test_geometry_audit_adds_qto_002_and_records_it(ingested, tmp_path):
    engine, ingest = ingested
    result = audits.run_audit(engine, ingest("clean"), geometry=True, files_dir=tmp_path / "files")
    assert result.counts["QTO-002"] == {"pass": 16} and result.reproducibility["geometry"] is True
    assert "QTO-002" not in audits.run_audit(engine, ingest("clean")).counts


def test_geometry_audit_keeps_volumes_for_the_quantities_report(ingested, tmp_path):
    # the API cannot run IFC processing, so it can only show volumes the audit job stored
    engine, ingest = ingested
    rev, files = ingest("clean"), tmp_path / "files"
    assert not any(r.method == "geometry" for r in quantities.report(engine, rev, files_dir=files))
    audits.run_audit(engine, rev, geometry=True, files_dir=files)
    geo = [r for r in quantities.report(engine, rev, files_dir=files) if r.method == "geometry"]
    assert geo and all(r.unit == "m3" and r.total > 0 for r in geo)
