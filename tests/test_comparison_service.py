from pathlib import Path

import pytest

from axiom.repo.db import get_engine, migrate
from axiom.services import audits, comparisons, projects, revisions

IDS = Path(__file__).parent.parent / "examples" / "ids" / "structural-basic.ids"


@pytest.fixture
def audited(tmp_path, ifc_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'axiom.db'}")
    migrate(engine)
    files = tmp_path / "files"
    model_id = projects.ensure_model(engine, "Demo", "Structure")

    def _audit(name: str, ids: Path | None = IDS, model: int = model_id) -> int:
        rev = revisions.ingest(engine, model, ifc_path(name), files_dir=files).revision_id
        audits.run_audit(engine, rev, ids_path=ids, files_dir=files)
        return rev

    return engine, _audit


def _events(result) -> dict:
    return {(e.rule_id, e.element_name): e.event for e in result.events if e.event != "persistent"}


def test_three_revisions_detect_recurring_and_persist(audited):
    engine, audit = audited
    r1, r2, r3 = audit("rev1"), audit("rev2"), audit("rev3")
    result = comparisons.compare(engine, r2, r3)
    assert _events(result) == {
        ("MAT-001", "C2"): "recurring",
        ("IDS:STR-COL", "C2"): "recurring",
        ("IDS:STR-WALL", "W1"): "new",
    }
    assert comparisons.load_events(engine, result.comparison_id) == result.events
    s = result.summary
    assert s["changes"] == {"modified": 2} and s["events"]["recurring"] == 2
    assert s["mhi"]["delta"] == pytest.approx(s["mhi"]["head"] - s["mhi"]["base"]) and s["mhi"]["delta"] < 0
    assert not s["ids_mismatch"] and not s["ruleset_mismatch"] and r1 < r2
    assert s["changes_by_class"] == {"IfcColumn": {"modified": 1}, "IfcWall": {"modified": 1}}
    assert s["mhi"]["dimensions"]["material_completeness"] < 0
    assert {"element_name": "C2", "rule_id": "MAT-001", "event": "recurring", "paths": ["material"]} in [
        {k: i[k] for k in ("element_name", "rule_id", "event", "paths")} for i in s["impact"]
    ]


def test_compare_with_previous_uses_the_prior_revision(audited):
    engine, audit = audited
    first = audit("rev1")
    assert comparisons.compare_with_previous(engine, first) is None
    result = comparisons.compare_with_previous(engine, audit("rev2"))
    assert result.base_revision_id == first
    assert _events(result)[("MAT-001", "C3")] == "resolved"


def test_ids_mismatch_is_flagged(audited):
    engine, audit = audited
    result = comparisons.compare(engine, audit("rev1", ids=None), audit("rev2"))
    assert result.summary["ids_mismatch"]


def test_unaudited_or_cross_model_compare_is_rejected(audited, ifc_path, tmp_path):
    engine, audit = audited
    other = projects.ensure_model(engine, "Demo", "Other")
    with pytest.raises(ValueError, match="same model"):
        comparisons.compare(engine, audit("rev1"), audit("rev2", model=other))
    bare = revisions.ingest(engine, other, ifc_path("rev3"), files_dir=tmp_path / "files").revision_id
    with pytest.raises(ValueError, match="no audit"):
        comparisons.compare(engine, audit("rev1", model=other), bare)


def test_ids_used_on_one_side_gives_uncertain_events(audited):
    engine, audit = audited
    audit("rev1")
    result = comparisons.compare(engine, audit("rev2", ids=None), audit("rev3"))
    events = {(e.rule_id, e.element_name): (e.event, e.note) for e in result.events}
    assert events[("IDS:STR-WALL", "W1")] == ("uncertain", "rule_not_evaluated_in_base")
    assert events[("MAT-001", "C2")][0] == "recurring"
