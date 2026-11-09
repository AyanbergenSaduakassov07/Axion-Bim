import pytest

from axiom.extract import extract
from axiom.quantities import aggregate, geometry_volumes, quantity_delta, run_qto_002

# Hand-computed from factory constants:
# column 0.3x0.3x3, beam 0.3x0.5x6, wall 6x3x0.2 (W6 is 3 m long), slab 6x6x0.2
CLEAN_BY_CLASS = {
    ("IfcBeam", "Length"): (24.0, "m", 4),
    ("IfcBeam", "GrossVolume"): (3.6, "m3", 4),
    ("IfcColumn", "Length"): (12.0, "m", 4),
    ("IfcColumn", "GrossVolume"): (1.08, "m3", 4),
    ("IfcSlab", "GrossArea"): (72.0, "m2", 2),
    ("IfcSlab", "GrossVolume"): (14.4, "m3", 2),
    ("IfcWall", "Length"): (33.0, "m", 6),
    ("IfcWall", "Height"): (18.0, "m", 6),
    ("IfcWall", "GrossVolume"): (19.8, "m3", 6),
}


def _table(rows):
    return {(r.group, r.quantity): (pytest.approx(r.total), r.unit, r.count) for r in rows}


@pytest.mark.parametrize("fixture", ["clean", "weird_units"])
def test_qto_totals_by_class_match_hand_values_in_any_unit(ifc_path, fixture):
    rows = aggregate(extract(ifc_path(fixture)), by="class")
    assert _table(rows) == CLEAN_BY_CLASS
    assert {r.method for r in rows} == {"qto"} and all(r.missing == () for r in rows)


def test_group_by_storey_and_material(ifc_path):
    snap = extract(ifc_path("clean"))
    storey = {(r.group, r.qto, r.quantity): r.total for r in aggregate(snap, by="storey")}
    assert storey[("Level 0", "Qto_ColumnBaseQuantities", "GrossVolume")] == pytest.approx(1.08)
    assert storey[("Level 1", "Qto_WallBaseQuantities", "GrossVolume")] == pytest.approx(19.8)
    material = {(r.group, r.quantity) for r in aggregate(snap, by="material")}
    assert ("C30/37", "GrossVolume") in material


def test_missing_quantity_is_listed_not_zeroed(ifc_path):
    snap = extract(ifc_path("clean"))
    c1 = next(e for e in snap.elements if e.name == "C1")
    stripped = snap.model_copy(
        update={
            "elements": tuple(
                e.model_copy(update={"quantities": ()}) if e is c1 else e for e in snap.elements
            )
        }
    )
    row = next(r for r in aggregate(stripped) if (r.group, r.quantity) == ("IfcColumn", "GrossVolume"))
    assert row.total == pytest.approx(0.81) and row.count == 3 and row.missing == (c1.global_id,)


def test_geometry_volumes_are_separate_rows_never_summed_with_qto(ifc_path):
    path = ifc_path("clean")
    snap = extract(path)
    volumes = geometry_volumes(path)
    assert volumes[next(e.step_id for e in snap.elements if e.name == "C1")] == pytest.approx(0.27)
    rows = aggregate(snap, geometry=volumes)
    geo = {r.group: r.total for r in rows if r.method == "geometry"}
    assert geo == {"IfcBeam": pytest.approx(3.6), "IfcColumn": pytest.approx(1.08),
                   "IfcSlab": pytest.approx(14.4), "IfcWall": pytest.approx(19.8)}  # fmt: skip
    keys = [(r.group, r.qto, r.quantity, r.method) for r in rows]
    assert len(keys) == len(set(keys))  # one method per total: no row mixes qto and geometry


def test_quantity_delta_between_revisions(ifc_path):
    old, new = aggregate(extract(ifc_path("rev1"))), aggregate(extract(ifc_path("rev2")))
    d = {(x.group, x.quantity): (x.old, x.new) for x in quantity_delta(old, new) if x.old != x.new}
    assert d[("IfcBeam", "Length")] == (pytest.approx(24.0), pytest.approx(30.0))  # +B5 (6 m)
    assert d[("IfcWall", "Length")] == (pytest.approx(33.0), pytest.approx(30.0))  # -W6 (3 m)


def _scaled(snap, name: str, factor: float):
    def fix(e):
        if e.name != name:
            return e
        qs = tuple(q.model_copy(update={"si_value": q.si_value * factor}) for q in e.quantities)
        return e.model_copy(update={"quantities": qs})

    return snap.model_copy(update={"elements": tuple(fix(e) for e in snap.elements)})


def test_qto_002_passes_consistent_volumes_and_flags_unit_scale_errors(ifc_path):
    path = ifc_path("clean")
    snap, volumes = extract(path), geometry_volumes(path)
    clean = run_qto_002(snap, volumes, model_id=1)
    assert clean.findings == () and clean.counts == {"QTO-002": {"pass": 16}}
    out = run_qto_002(_scaled(snap, "S1", 1000), volumes, model_id=1)
    (f,) = out.findings
    assert (f.rule_id, f.element_name, f.status, f.issue_key) == (
        "QTO-002",
        "S1",
        "fail",
        "volume:implausible",
    )
    assert f.evidence["ratio"] == pytest.approx(1000) and f.evidence["unit_scale_hint"] == 1000
    assert "7200" in f.actual and "7.2" in f.actual


def test_qto_002_without_geometry_is_not_evaluated(ifc_path):
    snap = extract(ifc_path("clean"))
    assert run_qto_002(snap, {}, model_id=1).counts == {"QTO-002": {"not_evaluated": 16}}
