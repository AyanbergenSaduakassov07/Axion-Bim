import pytest

from axiom.extract import extract
from axiom.revision import diff
from tests.conftest import load_expected

GOLDEN = load_expected("revisions")


def _summarise(result, old, new):
    names = {e.global_id: e.name for e in (*old.elements, *new.elements)}
    added = sorted(names[c.global_id] for c in result.changes if c.kind == "added")
    removed = sorted(names[c.global_id] for c in result.changes if c.kind == "removed")
    modified: dict[str, list[str]] = {}
    for c in result.changes:
        if c.kind == "modified":
            modified.setdefault(names[c.global_id], []).append(c.path)
    return {
        "added": added,
        "removed": removed,
        "modified": {k: sorted(v) for k, v in sorted(modified.items())},
    }


@pytest.mark.parametrize(("old", "new"), [("rev1", "rev2"), ("rev2", "rev3")])
def test_diff_matches_golden(ifc_path, old, new):
    a, b = extract(ifc_path(old)), extract(ifc_path(new))
    result = diff(a, b)
    golden = GOLDEN[f"{old}_{new}"]
    assert _summarise(result, a, b) == {k: golden[k] for k in ("added", "removed", "modified")}
    assert not result.identity_unstable and result.uncertain_global_ids == frozenset()


def test_modified_change_carries_old_and_new_values(ifc_path):
    result = diff(extract(ifc_path("rev1")), extract(ifc_path("rev2")))
    fire = next(c for c in result.changes if c.path == "pset:Pset_WallCommon.FireRating")
    assert (fire.old, fire.new, fire.ifc_class) == ("REI60", "REI90", "IfcWall")


def test_unit_change_alone_is_not_a_change(ifc_path):
    assert diff(extract(ifc_path("clean")), extract(ifc_path("weird_units"))).changes == ()


def test_regenerated_guids_flag_identity_unstable(ifc_path):
    old = extract(ifc_path("clean"))
    regen = tuple(e.model_copy(update={"global_id": f"X{e.global_id[1:]}"}) for e in old.elements)
    result = diff(old, old.model_copy(update={"elements": regen}))
    assert result.identity_unstable
    assert set(result.unstable_classes) == {"IfcColumn", "IfcBeam", "IfcWall", "IfcSlab"}


def test_duplicate_guids_are_uncertain_and_not_diffed(ifc_path):
    old, new = extract(ifc_path("clean")), extract(ifc_path("duplicate_guid"))
    result = diff(old, new)
    w1 = next(e.global_id for e in old.elements if e.name == "W1")
    assert result.uncertain_global_ids == frozenset({w1})
    assert all(c.global_id != w1 for c in result.changes)
