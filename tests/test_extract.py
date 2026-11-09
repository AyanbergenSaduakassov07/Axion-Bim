from collections import Counter

import ifcopenshell
import pytest

from axiom.extract import extract
from tests.conftest import load_expected
from tests.test_fixtures import FIXTURES


def by_name(snap, name):
    return next(e for e in snap.elements if e.name == name)


def storey_guid(snap, name):
    return next(n.global_id for n in snap.spatial if n.name == name)


@pytest.mark.parametrize("name", FIXTURES)
def test_element_counts_match_expected(name, ifc_path):
    snap = extract(ifc_path(name))
    assert dict(Counter(e.ifc_class for e in snap.elements)) == load_expected(name)["counts"]


def test_globalids_and_step_ids_round_trip(ifc_path):
    path = ifc_path("clean")
    snap = extract(path)
    f = ifcopenshell.open(path)
    assert {(e.global_id, e.step_id) for e in snap.elements} == {
        (e.GlobalId, e.id()) for e in f.by_type("IfcElement")
    }


def test_metadata(ifc_path):
    meta = extract(ifc_path("clean")).meta
    assert meta.schema_name == "IFC4"
    assert meta.project_name == "Axiom Fixture Project"
    assert meta.length_scale == 1.0
    assert meta.units["LENGTHUNIT"] == "METRE"
    assert len(meta.file_sha256) == 64
    assert meta.file_size > 0


def test_millimetre_quantities_normalize_to_metres(ifc_path):
    snap = extract(ifc_path("weird_units"))
    length = next(q for q in by_name(snap, "C2").quantities if q.name == "Length")
    assert (length.value, length.unit, length.si_value) == (3000.0, "MILLIMETRE", pytest.approx(3.0))
    volume = next(q for q in by_name(snap, "C2").quantities if q.name == "GrossVolume")
    assert volume.si_value == pytest.approx(0.27)
    assert snap.meta.length_scale == 0.001
    assert {n.name: n.elevation_m for n in snap.spatial if n.ifc_class == "IfcBuildingStorey"} == {
        "Level 0": 0.0,
        "Level 1": pytest.approx(3.0),
    }


def test_element_relations(ifc_path):
    snap = extract(ifc_path("uncontained"))
    c1, w6 = by_name(snap, "C1"), by_name(snap, "W6")
    assert c1.storey_global_id == storey_guid(snap, "Level 0")
    assert c1.has_representation and c1.representation_types == ("SweptSolid",)
    assert c1.materials[0].name == "C30/37" and c1.materials[0].kind == "IfcMaterial"
    assert c1.classifications[0].identification == "Ss_20_10_75_35"
    assert c1.classifications[0].system == "Uniclass 2015"
    assert (w6.storey_global_id, w6.container_global_id) == (None, None)


def test_properties_are_extracted_without_internal_ids(ifc_path):
    w1 = by_name(extract(ifc_path("clean")), "W1")
    props = {(p.pset, p.name): p.value for p in w1.properties}
    assert props[("Pset_WallCommon", "FireRating")] == "REI60"
    assert props[("Pset_WallCommon", "IsExternal")] is True
    assert not any(p.name == "id" for p in w1.properties)
    assert not any(p.pset.startswith("Qto_") for p in w1.properties)


def test_missing_data_is_none_not_invented(ifc_path):
    snap = extract(ifc_path("no_geometry"))
    b3 = by_name(snap, "B3")
    assert (b3.has_representation, b3.representation_types) == (False, ())
    assert by_name(extract(ifc_path("missing_material")), "C2").materials == ()
