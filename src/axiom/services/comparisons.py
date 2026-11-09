"""Compare two audited revisions of one model: element diff + finding events, persisted (P06, D-16)."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

from sqlalchemy import Connection, Engine

from axiom.repo import audits as audit_repo
from axiom.repo import comparisons as repo
from axiom.revision import DiffResult, FindingEvent, classify, diff, impact
from axiom.services.revisions import load_snapshot

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComparisonResult:
    comparison_id: int
    base_revision_id: int
    head_revision_id: int
    diff: DiffResult
    events: tuple[FindingEvent, ...]
    summary: dict


def compare(engine: Engine, base_revision_id: int, head_revision_id: int) -> ComparisonResult:
    """Uses the latest audit of each revision; history = latest audits of all audited revisions up to base."""
    with engine.connect() as conn:
        base, head = repo.revision_row(conn, base_revision_id), repo.revision_row(conn, head_revision_id)
        if base.model_id != head.model_id:
            raise ValueError("revisions must belong to the same model")
        base_run, head_run = _audit(conn, base_revision_id), _audit(conn, head_revision_id)
        history = [
            audit_repo.load_findings(conn, _audit(conn, r).id)
            for r in repo.audited_revisions(conn, base.model_id, base.seq)
        ]
        current = audit_repo.load_findings(conn, head_run.id)
    d = diff(load_snapshot(engine, base_revision_id), load_snapshot(engine, head_revision_id))
    evaluated = (set(base_run.summary_json["counts"]), set(head_run.summary_json["counts"]))
    events = classify(current, history, d, evaluated, _version_changed(base_run, head_run))
    summary = _summary(d, events, base_run, head_run)
    row = {
        "base_revision_id": base_revision_id,
        "head_revision_id": head_revision_id,
        "base_audit_run_id": base_run.id,
        "head_audit_run_id": head_run.id,
        "identity_unstable": d.identity_unstable,
        "summary_json": summary,
    }
    with engine.begin() as conn:
        cid = repo.insert_comparison(conn, row, d.changes, events)
    log.info("comparison %s: %s", cid, summary["events"])
    return ComparisonResult(cid, base_revision_id, head_revision_id, d, events, summary)


def compare_with_previous(engine: Engine, revision_id: int) -> ComparisonResult | None:
    """Compare against the previous revision of the same model, if there is one with an audit."""
    with engine.connect() as conn:
        rev = repo.revision_row(conn, revision_id)
        prev = repo.previous_revision_id(conn, rev.model_id, rev.seq)
        if prev is None or repo.latest_audit(conn, prev) is None:
            return None
    return compare(engine, prev, revision_id)


def load_events(engine: Engine, comparison_id: int) -> tuple[FindingEvent, ...]:
    with engine.connect() as conn:
        return repo.load_events(conn, comparison_id)


def _version_changed(base_run, head_run) -> set[str]:
    base, head = ({m["id"]: m["version"] for m in r.summary_json["rules"]} for r in (base_run, head_run))
    return {k for k, v in head.items() if base.get(k, v) != v}


def _audit(conn: Connection, revision_id: int):
    run = repo.latest_audit(conn, revision_id)
    if run is None:
        raise ValueError(f"revision {revision_id} has no audit; run `axiom audit` first")
    return run


def _summary(d: DiffResult, events: tuple[FindingEvent, ...], base_run, head_run) -> dict:
    by_class: dict[str, Counter] = defaultdict(Counter)
    for c in d.changes:
        by_class[c.ifc_class][c.kind] += 1
    return {
        "changes": dict(Counter(c.kind for c in d.changes)),
        "changes_by_class": {k: dict(v) for k, v in sorted(by_class.items())},
        "events": dict(Counter(e.event for e in events)),
        "mhi": _mhi_delta(base_run.summary_json["mhi"], head_run.summary_json["mhi"]),
        "impact": [asdict(i) | {"paths": list(i.paths)} for i in impact(d, events)],
        # events across different rule sets or IDS files mix "fixed" with "no longer checked"
        "ids_mismatch": base_run.ids_hash != head_run.ids_hash,
        "ruleset_mismatch": base_run.ruleset_version != head_run.ruleset_version,
        "unstable_classes": list(d.unstable_classes),
        "uncertain_global_ids": sorted(d.uncertain_global_ids),
    }


def _mhi_delta(base: dict, head: dict) -> dict:
    """Score delta plus per-dimension contribution delta (points of MHI each dimension moved)."""
    b, h = base["score"], head["score"]
    dims = {
        k: round(head["dimensions"][k]["contribution"] - base["dimensions"][k]["contribution"], 6)
        for k in head["dimensions"]
        if k in base["dimensions"]
    }
    return {
        "base": b,
        "head": h,
        "delta": None if b is None or h is None else round(h - b, 6),
        "dimensions": dims,
    }
