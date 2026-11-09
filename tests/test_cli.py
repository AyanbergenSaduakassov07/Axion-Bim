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
