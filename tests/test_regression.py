from pathlib import Path

import pytest

from axiom.extract import extract
from axiom.findings import Finding
from axiom.ids import run_ids
from axiom.revision import classify, diff, impact
from axiom.rules.engine import run_rules
from tests.conftest import load_expected

GOLDEN = load_expected("revisions")
STRUCTURAL = Path(__file__).parent.parent / "examples" / "ids" / "structural-basic.ids"
REVS = ("rev1", "rev2", "rev3")


def _events(evs) -> dict:
    out: dict[str, dict[str, str]] = {}
    for e in evs:
        if e.event != "persistent":
            out.setdefault(e.rule_id, {})[e.element_name] = e.event
    return out


@pytest.fixture(scope="module")
def revs(ifc_path):
    snaps = {r: extract(ifc_path(r)) for r in REVS}
    rules = {r: run_rules(snaps[r], model_id=1).findings for r in REVS}
    ids_ = {r: run_ids(ifc_path(r), STRUCTURAL, model_id=1).findings for r in REVS}
    return snaps, rules, ids_


@pytest.mark.parametrize("i", [1, 2])
@pytest.mark.parametrize(("source", "key"), [(1, "events"), (2, "ids_events")])
def test_events_match_golden(revs, i, source, key):
    snaps, findings = revs[0], revs[source]
    history = [findings[r] for r in REVS[:i]]
    d = diff(snaps[REVS[i - 1]], snaps[REVS[i]])
    got = _events(classify(findings[REVS[i]], history, d))
    assert got == GOLDEN[f"{REVS[i - 1]}_{REVS[i]}"][key]


def _f(key: str, gid: str = "g1", actual: str = "x") -> Finding:
    return Finding(
        identity_key=key, rule_id="R", rule_version="1", status="fail", severity="high", category="material",
        dimension="material", issue_key="i", global_id=gid, step_id=1, ifc_class="IfcWall", element_name="W",
        expected=None, actual=actual, message="m", evidence={},
    )  # fmt: skip


def test_changed_when_actual_differs():
    (e,) = classify([_f("k", actual="new")], [[_f("k", actual="old")]])
    assert e.event == "changed"


def test_first_audit_is_all_new_and_empty_history_ok():
    assert [e.event for e in classify([_f("k")], [])] == ["new"]


def test_uncertain_identity_overrides_everything(ifc_path):
    a = extract(ifc_path("clean"))
    d = diff(a, a)
    unstable = type(d)(d.changes, True, ("IfcWall",), frozenset())
    evs = classify([_f("k1")], [[_f("k2")]], unstable)
    assert sorted(e.event for e in evs) == ["uncertain", "uncertain"]


def test_resolved_by_removal_is_noted(ifc_path):
    a = extract(ifc_path("rev1"))
    gid = next(e.global_id for e in a.elements if e.name == "W6")
    (e,) = classify([], [[_f("k", gid=gid)]], diff(a, extract(ifc_path("rev2"))))
    assert e.event == "resolved" and e.note == "element_removed"


def test_rule_checked_on_one_side_only_is_uncertain_not_resolved_or_new():
    gone = classify([], [[_f("k")]], evaluated=({"R"}, set()))
    assert [(e.event, e.note) for e in gone] == [("uncertain", "rule_not_evaluated_in_head")]
    fresh = classify([_f("k")], [[]], evaluated=(set(), {"R"}))
    assert [(e.event, e.note) for e in fresh] == [("uncertain", "rule_not_evaluated_in_base")]


def test_impact_links_events_to_the_changes_on_their_element(revs):
    snaps, rules = revs[0], revs[1]
    d = diff(snaps["rev1"], snaps["rev2"])
    links = impact(d, classify(rules["rev2"], [rules["rev1"]], d))
    by_name = {(i.element_name, i.rule_id): (i.event, i.paths) for i in links}
    assert by_name == {
        ("C2", "MAT-001"): ("resolved", ("material",)),
        ("C3", "MAT-001"): ("resolved", ("material",)),
    }


def test_rule_whose_version_changed_gives_uncertain_not_resolved_or_new():
    # CLS-001 v1 -> v2 stopped flagging parts: that is the rule changing, not the model being fixed
    gone = classify([], [[_f("k")]], version_changed={"R"})
    assert [(e.event, e.note) for e in gone] == [("uncertain", "rule_version_changed")]
    fresh = classify([_f("k")], [[]], version_changed={"R"})
    assert [(e.event, e.note) for e in fresh] == [("uncertain", "rule_version_changed")]
    (same,) = classify([_f("k")], [[_f("k")]], version_changed={"R"})
    assert same.event == "persistent"  # identical output under both versions is still a fact
