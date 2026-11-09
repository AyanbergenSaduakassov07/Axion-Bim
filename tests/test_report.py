import csv
import io
import json
import os
import re
from pathlib import Path

import pytest

from axiom.repo.db import get_engine, migrate
from axiom.services import audits, comparisons, projects, reports, revisions

IDS = Path(__file__).parent.parent / "examples" / "ids" / "structural-basic.ids"
GOLDEN = Path(__file__).parent / "fixtures" / "expected" / "report_rev1_rev2.json"
# run-specific values: database ids, wall-clock times, and file hashes (owner-history timestamps vary)
VOLATILE = re.compile(r"(run|revision|comparison)_id$|created_at|file_sha256|file_size")


def _volatile(key: str, value) -> bool:
    if key == "id":
        return isinstance(value, int)  # database row id; rule ids are strings and stay
    return value is not None and bool(VOLATILE.search(key))


def _normalize(x):
    if isinstance(x, dict):
        return {k: "<volatile>" if _volatile(k, v) else _normalize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_normalize(v) for v in x]
    return x


@pytest.fixture
def rev2_audit(tmp_path, ifc_path) -> tuple:
    engine = get_engine(f"sqlite:///{tmp_path / 'axiom.db'}")
    migrate(engine)
    files = tmp_path / "files"
    model = projects.ensure_model(engine, "Demo", "Structure")
    runs = []
    for name in ("rev1", "rev2"):
        rev = revisions.ingest(engine, model, ifc_path(name), files_dir=files).revision_id
        runs.append(audits.run_audit(engine, rev, ids_path=IDS, files_dir=files))
    comparisons.compare(engine, runs[0].revision_id, runs[1].revision_id)
    return engine, runs[1].audit_run_id


def test_report_json_matches_golden(rev2_audit):
    engine, audit_id = rev2_audit
    got = _normalize(json.loads(json.dumps(reports.build(engine, audit_id), default=str)))
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(json.dumps(got, indent=2, sort_keys=True) + "\n")
    assert got == json.loads(GOLDEN.read_text())


def test_report_includes_comparison_events_and_reproducibility(rev2_audit):
    engine, audit_id = rev2_audit
    r = reports.build(engine, audit_id)
    assert r["comparison"]["base"]["seq"] == 1 and r["comparison"]["head"]["seq"] == 2
    assert {e["event"] for e in r["comparison"]["events"]} >= {"resolved"}
    assert {"file_sha256", "ruleset_version", "ids_hash", "engine_version"} <= r["reproducibility"].keys()


def test_csv_has_one_row_per_finding(rev2_audit):
    engine, audit_id = rev2_audit
    first = reports.build(engine, audit_id - 1)  # rev1 audit has failures
    rows = list(csv.DictReader(io.StringIO(reports.render(first, "csv"))))
    assert len(rows) == len(first["findings"]) > 0
    assert {"global_id", "rule_id", "status", "expected", "actual"} <= rows[0].keys()


def test_html_is_self_contained_and_escaped(rev2_audit):
    engine, audit_id = rev2_audit
    html = reports.render(reports.build(engine, audit_id - 1), "html")
    assert "<html" in html and "@media print" in html
    assert not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", html)
    assert "@import" not in html and "<script" not in html


def test_unknown_format_and_missing_audit_raise(rev2_audit):
    engine, audit_id = rev2_audit
    with pytest.raises(ValueError):
        reports.render(reports.build(engine, audit_id), "pdf")
    with pytest.raises(LookupError):
        reports.build(engine, 999)


def test_findings_carry_element_origin_for_viewpoints(rev2_audit):
    engine, audit_id = rev2_audit
    findings = reports.build(engine, audit_id - 1)["findings"]  # rev1 has element-level failures
    placed = [f for f in findings if f["global_id"]]
    assert placed and all(len(f["origin_m"]) == 3 for f in placed)
    assert all(f["origin_m"] is None for f in findings if not f["global_id"])
