"""Project dashboard (D-33): MHI trend per model and issue KPIs over each model's latest audit."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date

from sqlalchemy import Connection, Engine, Row

from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import comparisons as cmp_repo
from axiom.repo import issues as issue_repo
from axiom.services.issues import STATES

DONE = frozenset({"accepted", "closed"})
Triage = tuple[str, str | None, date | None]  # state, assignee, due date


def issue_tally(rows: Iterable[tuple[str, str]], issues: dict[str, Triage], today: date) -> dict:
    """Counts over findings; a finding with no triage row is open. Done = accepted or closed."""
    states: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    active: Counter[str] = Counter()
    late: Counter[str | None] = Counter()  # None = unassigned
    unassigned = 0
    for key, rule_id in rows:
        state, assignee, due = issues.get(key, ("open", None, None))
        states[state] += 1
        if state in DONE:
            continue
        rules[rule_id] += 1
        overdue = due is not None and due < today
        if assignee:
            active[assignee] += 1
            late[assignee] += overdue
        else:
            unassigned += 1
            late[None] += overdue
    return {
        "states": {s: states[s] for s in STATES},
        "overdue": sum(late.values()),
        "unassigned": unassigned,
        "by_assignee": [{"assignee": a, "active": n, "overdue": late[a]} for a, n in active.most_common()],
        "by_rule": [{"rule_id": r, "active": n} for r, n in rules.most_common()],
    }


def _trend(conn: Connection, model_id: int) -> tuple[list[dict], Row | None]:
    points, last = [], None
    for rev in repo.list_revisions(conn, model_id):
        audit = cmp_repo.latest_audit(conn, rev.id)
        if audit is None:
            continue
        mhi = audit.summary_json.get("mhi", {})
        points.append(
            {
                "revision_id": rev.id,
                "seq": rev.seq,
                "created_at": rev.created_at,
                "score": mhi.get("score"),
                "coverage": mhi.get("coverage"),
            }
        )
        last = audit
    return points, last


def project_dashboard(engine: Engine, project_id: int, today: date) -> dict:
    with engine.connect() as conn:
        project = repo.get_project(conn, project_id)
        if project is None:
            raise LookupError(f"project {project_id} not found")
        models, rows, triage = [], [], {}
        for m in repo.list_models(conn, project_id):
            trend, audit = _trend(conn, m.id)
            keys = audit_repo.finding_keys(conn, audit.id) if audit else []
            # identity keys embed the model id, so merging models into one dict cannot collide
            triage |= {
                i.identity_key: (i.state, i.assignee, i.due_date) for i in issue_repo.list_issues(conn, m.id)
            }
            rows += keys
            models.append({"model_id": m.id, "name": m.name, "trend": trend, "findings": len(keys)})
    return {
        "project_id": project_id,
        "name": project.name,
        "models": models,
        "issues": issue_tally(rows, triage, today),
    }
