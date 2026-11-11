"""Issue digest per assignee as Markdown (D-40): pastes into email, Telegram or a chat as it is."""

from __future__ import annotations


def _line(i: dict) -> str:
    element = " ".join(x for x in (i["ifc_class"], i["element_name"], i["global_id"]) if x) or "model level"
    due = ""
    if i["overdue"]:
        due = f" — **overdue since {i['due_date']}**"
    elif i["due_date"]:
        due = f" — due {i['due_date']}"
    state = "" if i["state"] == "open" else f" ({i['state']})"
    return f"- {i['model']} · {i['rule_id']} · {element}{state}{due}"


def to_markdown(digest: dict) -> str:
    out = [f"# Open issues on {digest['today']}", ""]
    for a in digest["assignees"]:
        out += [f"## {a['assignee']} — {len(a['items'])} open, {a['overdue']} overdue", ""]
        out += [_line(i) for i in a["items"]] + [""]
    if digest["unassigned"]:
        out.append(f"{digest['unassigned']} open findings have no assignee.")
    if not digest["assignees"] and not digest["unassigned"]:
        out.append("Nothing open.")
    return "\n".join(out).rstrip() + "\n"
