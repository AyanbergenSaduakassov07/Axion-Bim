"""Every generated fixture must match its hand-authored expected.yaml, observed via ifcopenshell only."""

from collections import Counter

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu
import numpy as np
import pytest

from tests.conftest import EXPECTED_DIR, load_expected
from tests.fixtures.factory import build_fixture

FIXTURES = sorted(p.stem for p in EXPECTED_DIR.glob("*.yaml"))
STRUCTURAL = ("IfcColumn", "IfcBeam", "IfcSlab")


def observed_defects(f) -> dict[str, list]:
    elems = [e for e in f.by_type("IfcElement") if not e.is_a("IfcOpeningElement")]
    names = Counter(e.GlobalId for e in elems)
    by_guid: dict[str, list[str]] = {}
    for e in elems:
        by_guid.setdefault(e.GlobalId, []).append(e.Name)
    return {
        "missing_material": sorted(
            e.Name for e in elems if e.is_a() in STRUCTURAL and not ue.get_material(e)
        ),
        "missing_fire_rating": sorted(
            e.Name
            for e in elems
            if e.is_a("IfcWall") and "FireRating" not in ue.get_psets(e).get("Pset_WallCommon", {})
        ),
        "no_geometry": sorted(e.Name for e in elems if e.Representation is None),
        "uncontained": sorted(e.Name for e in elems if ue.get_container(e) is None),
        "duplicate_guid": sorted(sorted(by_guid[g]) for g, n in names.items() if n > 1),
    }


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_matches_expected(name, ifc_path):
    exp = load_expected(name)
    f = ifcopenshell.open(ifc_path(name))

    assert f.schema == exp["schema"]
    assert uu.calculate_unit_scale(f) == pytest.approx(exp["length_scale"])
    assert [s.Name for s in sorted(f.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation)] == exp[
        "storeys"
    ]
    counts = Counter(e.is_a() for e in f.by_type("IfcElement"))
    assert {k: counts[k] for k in exp["counts"]} == exp["counts"]
    assert sum(counts.values()) == sum(exp["counts"].values()), f"unexpected extra elements: {counts}"
    for el_name, mat in exp.get("materials", {}).items():
        el = next(e for e in f.by_type("IfcElement") if e.Name == el_name)
        assert ue.get_material(el).Name == mat
    obs = observed_defects(f)
    for key, want in exp["defects"].items():
        assert obs[key] == sorted(want), key


def test_globalids_are_stable_across_builds(ifc_path, tmp_path):
    a = ifcopenshell.open(ifc_path("clean"))
    b = ifcopenshell.open(build_fixture("clean", tmp_path))
    assert {e.Name: e.GlobalId for e in a.by_type("IfcElement")} == {
        e.Name: e.GlobalId for e in b.by_type("IfcElement")
    }


# Hand-computed world AABBs in metres: (min xyz, max xyz). Beam top = storey height, slab top = storey level.
EXPECTED_AABB = {
    "C2": ((5.85, -0.15, 0.0), (6.15, 0.15, 3.0)),
    "B1": ((0.0, -0.15, 2.5), (6.0, 0.15, 3.0)),
    "B3": ((-0.15, 0.0, 2.5), (0.15, 6.0, 3.0)),
    "W2": ((5.8, 0.0, 3.0), (6.0, 6.0, 6.0)),
    "S1": ((0.0, 0.0, -0.2), (6.0, 6.0, 0.0)),
}


def world_aabb(f, name: str) -> np.ndarray:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    el = next(e for e in f.by_type("IfcElement") if e.Name == name)
    verts = np.array(ifcopenshell.geom.create_shape(settings, el).geometry.verts).reshape(-1, 3)
    return np.array([verts.min(0), verts.max(0)])


@pytest.mark.parametrize("fixture", ["clean", "weird_units"])
def test_geometry_lands_where_expected_in_si(fixture, ifc_path):
    f = ifcopenshell.open(ifc_path(fixture))
    for name, box in EXPECTED_AABB.items():
        np.testing.assert_allclose(world_aabb(f, name), box, atol=1e-6, err_msg=name)
