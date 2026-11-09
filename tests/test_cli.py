import json

from typer.testing import CliRunner

from axiom.cli import app

runner = CliRunner()


def test_inspect_json_reports_metadata_and_profile(ifc_path):
    result = runner.invoke(app, ["inspect", str(ifc_path("missing_material")), "--json"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.output)
    assert out["meta"]["schema_name"] == "IFC4"
    assert out["profile"]["by_class"]["IfcColumn"]["missing"]["material"] == 2


def test_inspect_text_mentions_counts(ifc_path):
    result = runner.invoke(app, ["inspect", str(ifc_path("clean"))])
    assert result.exit_code == 0, result.output
    assert "IfcColumn" in result.output and "16 elements" in result.output


def test_inspect_missing_file_fails_cleanly(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "nope.ifc")])
    assert result.exit_code != 0


def test_audit_writes_json_report_with_reproducibility(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AXIOM_DB_URL", raising=False)
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["audit", str(ifc_path("missing_material")), "--json", str(out)])
    assert result.exit_code == 0, result.output
    assert "MAT-001" in result.output and "C2" in result.output
    report = json.loads(out.read_text())
    assert report["reproducibility"]["ruleset_version"]
    assert sorted(f["element_name"] for f in report["findings"]) == ["C2", "C3"]
    assert report["counts"]["MAT-001"] == {"pass": 8, "fail": 2}
    assert (tmp_path / "data" / "axiom.db").exists()


def test_audit_with_ids_shows_expected_vs_actual(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AXIOM_DB_URL", raising=False)
    ids = "examples/ids/structural-basic.ids"
    result = runner.invoke(app, ["audit", str(ifc_path("missing_props")), "--ids", ids])
    assert result.exit_code == 0, result.output
    assert "IDS:STR-WALL" in result.output and "W3" in result.output
    assert "expected: FireRating data shall be provided in the dataset Pset_WallCommon" in result.output
    assert "actual: The property set does not contain the required property" in result.output


def test_audit_with_invalid_ids_fails_cleanly(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    bad = tmp_path / "bad.ids"
    bad.write_text("<ids/>")
    result = runner.invoke(app, ["audit", str(ifc_path("clean")), "--ids", str(bad)])
    assert result.exit_code == 2
    assert "invalid IDS" in result.output


def test_audit_prints_mhi_table_and_gate(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    out = tmp_path / "r.json"
    result = runner.invoke(app, ["audit", str(ifc_path("duplicate_guid")), "--json", str(out)])
    assert result.exit_code == 0, result.output
    assert "MHI" in result.output and "model_consistency" in result.output
    assert "BLOCKED" in result.output
    assert json.loads(out.read_text())["mhi"]["blocked"] is True


def test_compare_three_revisions_reports_events_and_mhi_delta(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AXIOM_DB_URL", raising=False)
    files = [str(ifc_path(r)) for r in ("rev1", "rev2", "rev3")]
    out = tmp_path / "cmp.json"
    ids = "examples/ids/structural-basic.ids"
    result = runner.invoke(app, ["compare", *files, "--ids", ids, "--json", str(out)])
    assert result.exit_code == 0, result.output
    assert "revision 2 -> 3" in result.output and "recurring" in result.output and "MHI" in result.output
    report = json.loads(out.read_text())
    assert [c["summary"]["changes"] for c in report] == [
        {"added": 1, "removed": 1, "modified": 4},
        {"modified": 2},
    ]
    events = {(e["rule_id"], e["element_name"]): e["event"] for e in report[1]["events"]}
    assert events[("IDS:STR-WALL", "W1")] == "new" and events[("MAT-001", "C2")] == "recurring"
    assert any(c["path"] == "pset:Pset_WallCommon.FireRating" for c in report[0]["changes"])


def test_compare_needs_two_files(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    result = runner.invoke(app, ["compare", str(ifc_path("rev1"))])
    assert result.exit_code == 2


def test_audit_auto_compares_with_previous_revision(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AXIOM_DB_URL", raising=False)
    runner.invoke(app, ["audit", str(ifc_path("rev1")), "--model", "S"])
    result = runner.invoke(app, ["audit", str(ifc_path("rev2")), "--model", "S"])
    assert result.exit_code == 0, result.output
    assert "vs revision 1" in result.output and "resolved 2" in result.output
