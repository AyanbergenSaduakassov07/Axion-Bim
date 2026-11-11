"""Acceptance gate (D-36): the delivery decision, derived from open findings and a project threshold.

Pure: no DB, no IFC. Decision words are their own vocabulary, distinct from finding statuses and
revision events.
A delivery is never `accepted` when the score or the client requirements (IDS) were not evaluated.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from axiom.findings import Severity

DECISIONS = ("accepted", "accepted_with_comments", "rejected", "undecided")
OPEN_STATUSES = ("fail", "warning")
_RANK = {s.value: i for i, s in enumerate(Severity)}  # critical = 0


@dataclass(frozen=True)
class GatePolicy:
    min_score: float = 80.0
    block_severity: str = "critical"  # an open `fail` at this severity or above rejects the delivery
    require_ids: bool = True


def decide(
    score: float | None,
    findings: Iterable[tuple[str, str, str]],
    *,
    waived: set[str],
    ids_checked: bool,
    policy: GatePolicy,
) -> dict:
    """`findings` are (severity, status, identity_key); `waived` are keys the reviewer took as they are."""
    raised = [f for f in findings if f[1] in OPEN_STATUSES]
    open_ = [f for f in raised if f[2] not in waived]
    limit = _RANK[policy.block_severity]
    blocking = sum(1 for sev, status, _ in open_ if status == "fail" and _RANK[sev] <= limit)
    below = score is not None and score < policy.min_score
    unchecked = policy.require_ids and not ids_checked

    reasons: list[dict] = []
    if blocking:
        reasons.append({"code": "blocking_findings", "n": blocking})
    if below:
        reasons.append({"code": "score_below_minimum", "score": score, "minimum": policy.min_score})
    if unchecked:
        reasons.append({"code": "ids_not_evaluated"})
    if score is None:
        reasons.append({"code": "score_not_evaluated"})
    if open_:
        reasons.append({"code": "open_findings", "n": len(open_)})
    if len(raised) > len(open_):
        reasons.append({"code": "waived", "n": len(raised) - len(open_)})

    if blocking or below:
        decision = "rejected"
    elif unchecked or score is None:
        decision = "undecided"
    else:
        decision = "accepted_with_comments" if raised else "accepted"  # a waiver is still a comment
    return {"decision": decision, "reasons": reasons}
