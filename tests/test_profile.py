import pytest

from axiom.extract import extract, profile


def test_profile_counts_and_gaps(ifc_path):
    p = profile(extract(ifc_path("missing_material")))
    assert p["total_elements"] == 16
    assert p["by_class"]["IfcColumn"]["count"] == 4
    assert p["by_class"]["IfcColumn"]["missing"]["material"] == 2
    assert p["by_class"]["IfcWall"]["missing"] == {
        "name": 0,
        "psets": 0,
        "material": None,
        "geometry": 0,
        "containment": 0,
    }


@pytest.mark.parametrize(
    ("fixture", "cls", "gap", "n"),
    [("no_geometry", "IfcBeam", "geometry", 2), ("uncontained", "IfcWall", "containment", 1)],
)
def test_profile_detects_gap(fixture, cls, gap, n, ifc_path):
    assert profile(extract(ifc_path(fixture)))["by_class"][cls]["missing"][gap] == n


def test_completeness_is_share_of_applicable_checks_passed(ifc_path):
    # 4 columns x 5 checks = 20, two columns lack material -> 18/20
    assert profile(extract(ifc_path("missing_material")))["by_class"]["IfcColumn"]["completeness"] == 0.9
    assert profile(extract(ifc_path("clean")))["completeness"] == 1.0
