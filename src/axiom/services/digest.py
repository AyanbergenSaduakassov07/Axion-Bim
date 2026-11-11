"""Who has what open, over each model's latest audit (D-40). Same done-states as the dashboard."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import Engine

from axiom.repo import audits as audit_repo
from axiom.repo import browse as repo
from axiom.repo import comparisons as cmp_repo
from axiom.repo import issues as issue_repo
from axiom.services.dashboard import DONE


def _items(conn, model, today: date) -> tuple[dict[str, list[dict]], int]:
    revs = repo.list_revisions(conn, model.id)
    audit = cmp_repo.latest_audit(conn, revs[-1].id) if revs else None
    if audit is None:
        return {}, 0
    triage = {i.identity_key: i for i in issue_repo.list_issues(conn, model.id)}
    by_person: dict[str, list[dict]] = defaultdict(list)
    unassigned = 0
    for f in {f.identity_key: f for f in audit_repo.load_findings(conn, audit.id)}.values():
        t = triage.get(f.identity_key)
        state = t.state if t else "open"
        if state in DONE:
            continue
        if not (t and t.assignee):
            unassigned += 1
            continue
        due = t.due_date
        by_person[t.assignee].append(
            {
                "model": model.name,
                "rule_id": f.rule_id,
                "global_id": f.global_id,
                "ifc_class": f.ifc_class,
                "element_name": f.element_name,
                "state": state,
                "due_date": due,
                "overdue": due is not None and due < today,
            }
        )
    return by_person, unassigned


def project_digest(engine: Engine, project_id: int, today: date) -> dict:
    with engine.connect() as conn:
        if repo.get_project(conn, project_id) is None:
            raise LookupError(f"project {project_id} not found")
        people: dict[str, list[dict]] = defaultdict(list)
        unassigned = 0
        for m in repo.list_models(conn, project_id):
            items, n = _items(conn, m, today)
            unassigned += n
            for person, rows in items.items():
                people[person] += rows
    assignees = [
        {
            "assignee": person,
            "overdue": sum(i["overdue"] for i in rows),
            "items": sorted(rows, key=lambda i: (not i["overdue"], i["due_date"] or date.max, i["rule_id"])),
        }
        for person, rows in people.items()
    ]
    assignees.sort(key=lambda a: (-a["overdue"], a["assignee"]))
    return {"today": today, "unassigned": unassigned, "assignees": assignees}
