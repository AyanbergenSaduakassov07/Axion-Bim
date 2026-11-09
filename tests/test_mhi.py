import random

import pytest

from axiom.findings import Finding
from axiom.rules import builtin_rules
from axiom.score import ScoringConfig, compute_mhi, load_config

CFG = ScoringConfig(
    version="t1",
    weights={"geometry": 0.5, "spatial": 0.3, "consistency": 0.2},
    rules={"GEO-001": "geometry", "SPA-*": "spatial", "GEO-002": "consistency"},
)


def _critical(key: str = "k1") -> Finding:
    return Finding(
        identity_key=key, rule_id="GEO-002", rule_version="1", status="fail", severity="critical",
        category="identity", dimension="identity", issue_key="guid:duplicate", global_id="g", step_id=None,
        ifc_class=None, element_name=None, expected=None, actual=None, message="dup", evidence={},
    )  # fmt: skip


def test_all_pass_scores_100_with_full_coverage():
    counts = {"GEO-001": {"pass": 10}, "SPA-001": {"pass": 4}, "GEO-002": {"pass": 16}}
    r = compute_mhi(counts, (), CFG)
    assert r.score == 100 and r.coverage == 100 and not r.blocked and r.notes == ()


def test_empty_dimension_redistributes_weight_exactly():
    counts = {"GEO-001": {"pass": 3, "fail": 1}, "GEO-002": {"pass": 1}}
    r = compute_mhi(counts, (), CFG)
    spatial = r.dimensions["spatial"]
    assert spatial.score is None and spatial.effective_weight == 0
    assert r.dimensions["geometry"].effective_weight == pytest.approx(5 / 7)
    assert r.score == pytest.approx(100 * (0.75 * 5 + 1.0 * 2) / 7)  # 82.142857...
    assert any("spatial" in n for n in r.notes)


def test_critical_fail_blocks_even_at_high_score():
    counts = {"GEO-001": {"pass": 100}, "SPA-001": {"pass": 100}, "GEO-002": {"pass": 98, "fail": 1}}
    r = compute_mhi(counts, (_critical("dup-1"),), CFG)
    assert r.score > 98 and r.blocked and r.blocking == ("dup-1",)


def test_not_evaluated_is_coverage_not_failure():
    counts = {"GEO-001": {"pass": 4}, "SPA-001": {"not_evaluated": 4}, "GEO-002": {"pass": 4, "error": 0}}
    r = compute_mhi(counts, (), CFG)
    assert r.dimensions["spatial"].score is None and r.dimensions["spatial"].not_evaluated == 4
    assert r.score == 100 and r.coverage == pytest.approx(100 * 8 / 12)


def test_warnings_only_dimension_is_null_and_noted():
    cfg = ScoringConfig(version="t", weights={"geometry": 0.6, "classification": 0.4},
                        rules={"GEO-001": "geometry", "CLS-001": "classification"})  # fmt: skip
    r = compute_mhi({"GEO-001": {"pass": 2}, "CLS-001": {"warning": 2}}, (), cfg)
    assert r.dimensions["classification"].score is None and r.dimensions["classification"].warnings == 2
    assert r.score == 100 and r.coverage == 100
    assert any("classification" in n for n in r.notes)


def test_unmapped_rule_is_noted_not_scored():
    r = compute_mhi({"GEO-001": {"pass": 1}, "XYZ-9": {"fail": 5}}, (), CFG)
    assert r.score == 100 and any("XYZ-9" in n for n in r.notes)


def test_nothing_evaluated_gives_null_score():
    r = compute_mhi({}, (), CFG)
    assert r.score is None and r.coverage is None


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        ScoringConfig(version="x", weights={"a": 0.5, "b": 0.4}, rules={})
    with pytest.raises(ValueError, match="unknown dimension"):
        ScoringConfig(version="x", weights={"a": 1.0}, rules={"R": "b"})


def test_score_always_within_bounds():
    rng = random.Random(7)
    for _ in range(500):
        counts = {
            rid: {s: rng.randint(0, 5) for s in ("pass", "fail", "warning", "not_evaluated", "error")}
            for rid in ("GEO-001", "SPA-001", "SPA-002", "GEO-002")
            if rng.random() > 0.3
        }
        r = compute_mhi(counts, (), CFG)
        assert r.score is None or 0 <= r.score <= 100
        assert r.coverage is None or 0 <= r.coverage <= 100


def test_default_config_maps_every_builtin_rule_and_ids():
    cfg = load_config()
    assert abs(sum(cfg.weights.values()) - 1) < 1e-9
    for r in builtin_rules():
        assert cfg.dimension_of(r.meta.id) is not None, r.meta.id
    assert cfg.dimension_of("IDS:STR-WALL") == "ids_compliance"
