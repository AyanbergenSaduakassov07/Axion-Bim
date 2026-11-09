from pathlib import Path

import ifcopenshell
import ifcopenshell.guid
import pytest

from axiom.ids import run_ids

ROOT = Path(__file__).parent.parent
STRUCTURAL = ROOT / "examples" / "ids" / "structural-basic.ids"
EDGE = Path(__file__).parent / "fixtures" / "ids" / "edge.ids"


def _failed(out, rule_id):
    return sorted(f.element_name for f in out.findings if f.rule_id == rule_id and f.status == "fail")


def test_missing_fire_rating_is_reported_per_wall(ifc_path):
    out = run_ids(ifc_path("missing_props"), STRUCTURAL, model_id=1)
    assert _failed(out, "IDS:STR-WALL") == ["W1", "W2", "W3"]
    assert out.counts["IDS:STR-WALL"] == {"pass": 3, "fail": 3}
    f = next(f for f in out.findings if f.rule_id == "IDS:STR-WALL")
    assert f.issue_key == "2/property/Pset_WallCommon.FireRating"
    assert "FireRating" in f.expected and "Pset_WallCommon" in f.expected
    assert f.actual and f.severity == "high" and f.category == "information"
    assert f.global_id and f.step_id and f.ifc_class == "IfcWall"


def test_missing_material_hits_only_the_material_facet(ifc_path):
    out = run_ids(ifc_path("missing_material"), STRUCTURAL, model_id=1)
    col = [f for f in out.findings if f.rule_id == "IDS:STR-COL"]
    assert sorted(f.element_name for f in col) == ["C2", "C3"]
    assert {f.issue_key for f in col} == {"0/material/any"}
    assert out.counts["IDS:STR-COL"] == {"pass": 6, "fail": 2}  # 4 columns x 2 requirements
    assert _failed(out, "IDS:STR-BEAM") == []


def test_rev3_regression_is_one_wall(ifc_path):
    out = run_ids(ifc_path("rev3"), STRUCTURAL, model_id=1)
    assert _failed(out, "IDS:STR-WALL") == ["W1"]


def test_clean_model_has_no_findings_and_versioned_rules(ifc_path):
    out = run_ids(ifc_path("clean"), STRUCTURAL, model_id=1)
    assert out.findings == ()
    assert [m.id for m in out.rules] == ["IDS:STR-COL", "IDS:STR-BEAM", "IDS:STR-WALL"]
    assert len({m.version for m in out.rules}) == 1 and len(out.rules[0].version) == 12


def test_cardinality_edges(ifc_path):
    out = run_ids(ifc_path("clean"), EDGE, model_id=1)
    req = [f for f in out.findings if f.rule_id == "IDS:footings required"]
    assert len(req) == 1 and req[0].global_id is None and req[0].issue_key == "0/applicability/min_occurs"
    assert out.counts["IDS:footings required"] == {"fail": 1}
    assert out.counts["IDS:footings optional"] == {"not_applicable": 1}
    assert _failed(out, "IDS:no beams allowed") == ["B1", "B2", "B3", "B4"]
    assert out.counts["IDS:ifc2x3 only"] == {"not_applicable": 1}


def test_subtype_coverage_gap_is_flagged(tmp_path, ifc_path):
    f = ifcopenshell.open(ifc_path("clean"))
    f.createIfcWallStandardCase(ifcopenshell.guid.new(), None, "WSC", None, None, None, None, None, None)
    path = tmp_path / "subtype.ifc"
    f.write(str(path))
    out = run_ids(path, STRUCTURAL, model_id=1)
    hint = [x for x in out.findings if x.issue_key == "2/coverage/subtypes"]
    assert len(hint) == 1 and hint[0].status == "warning" and hint[0].severity == "info"
    assert hint[0].evidence["uncovered"] == {"IfcWallStandardCase": 1}
    assert _failed(out, "IDS:STR-WALL") == []


def test_invalid_ids_is_rejected(tmp_path, ifc_path):
    bad = tmp_path / "bad.ids"
    bad.write_text("<ids/>")
    with pytest.raises(ValueError, match="IDS"):
        run_ids(ifc_path("clean"), bad, model_id=1)


def test_specs_sharing_a_name_keep_separate_counts(tmp_path, ifc_path):
    dup = tmp_path / "dup.ids"
    dup.write_text(EDGE.read_text().replace('name="footings optional"', 'name="footings required"'))
    out = run_ids(ifc_path("clean"), dup, model_id=1)
    assert out.counts["IDS:footings required"] == {"fail": 1}
    assert out.counts["IDS:footings required#1"] == {"not_applicable": 1}
