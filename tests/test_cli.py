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
