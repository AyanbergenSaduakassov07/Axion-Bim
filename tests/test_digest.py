"""Issue digest per assignee: what each person has open, overdue first (D-40, audit gap G10 / F6)."""

from datetime import date

from typer.testing import CliRunner

from axiom.cli import app
from axiom.digest import to_markdown
from axiom.repo.db import get_engine, migrate
from axiom.services import browse, digest, issues, projects
from axiom.services.audits import run_audit
from axiom.services.revisions import ingest

TODAY = date(2026, 11, 11)


def _item(rule, due, *, overdue, state="open"):
    return {
        "model": "STR",
        "rule_id": rule,
        "global_id": "2O2Fr$t4X7Zf8NOew3FLOH",
        "ifc_class": "IfcColumn",
        "element_name": "C2",
        "state": state,
        "due_date": due,
        "overdue": overdue,
    }


def test_markdown_lists_each_assignee_with_overdue_first_and_counts_unassigned():
    d = {
        "today": TODAY,
        "unassigned": 3,
        "assignees": [
            {
                "assignee": "Dana",
                "overdue": 1,
                "items": [
                    _item("MAT-001", date(2026, 11, 1), overdue=True),
                    _item("QTO-001", None, overdue=False, state="disputed"),
                ],
            },
        ],
    }
    md = to_markdown(d)
    assert md.splitlines()[0] == "# Open issues on 2026-11-11"
    assert "## Dana — 2 open, 1 overdue" in md
    assert md.index("MAT-001") < md.index("QTO-001")
    assert "**overdue since 2026-11-01**" in md and "disputed" in md
    assert "3 open findings have no assignee." in md


def test_digest_takes_the_latest_audit_skips_done_issues_and_sorts_overdue_first(ifc_path, tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'a.db'}")
    migrate(engine)
    mid = projects.ensure_model(engine, "Demo", "STR")
    rev = ingest(engine, mid, ifc_path("rev1"), files_dir=tmp_path).revision_id  # 2 findings
    later, late = [f.identity_key for f in run_audit(engine, rev, files_dir=tmp_path).findings]
    issues.update(engine, mid, [later], {"assignee": "Dana", "due_date": date(2026, 12, 1)})
    issues.update(engine, mid, [late], {"assignee": "Dana", "due_date": date(2026, 11, 1)})
    pid = next(p["id"] for p in browse.list_projects(engine) if p["name"] == "Demo")

    (dana,) = digest.project_digest(engine, pid, TODAY)["assignees"]
    assert dana["assignee"] == "Dana" and dana["overdue"] == 1
    assert [i["overdue"] for i in dana["items"]] == [True, False]

    issues.update(engine, mid, [late], {"state": "closed"})
    d = digest.project_digest(engine, pid, TODAY)
    assert [len(a["items"]) for a in d["assignees"]] == [1] and d["unassigned"] == 0


def test_digest_command_prints_markdown_and_rejects_an_unknown_project(ifc_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AXIOM_DATA_DIR", str(tmp_path / "data"))
    runner = CliRunner()
    assert runner.invoke(app, ["audit", str(ifc_path("rev1")), "--project", "Demo"]).exit_code == 0
    out = runner.invoke(app, ["digest", "--project", "Demo"])
    assert out.exit_code == 0 and out.output.startswith("# Open issues on ")
    assert "have no assignee" in out.output
    assert runner.invoke(app, ["digest", "--project", "Nope"]).exit_code == 2
