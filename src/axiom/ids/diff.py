"""What changed between two versions of a requirements file (IDS): specifications added, removed, changed."""

from __future__ import annotations

from ifctester import ids

PARTS = ("applicability", "requirements", "@name", "@ifcVersion", "@description", "@instructions")


def _specs(doc: ids.Ids) -> dict[str, dict]:
    # shortcut: two specifications sharing an identifier (or, without one, a name) collapse to the last;
    # key by position as well if a client file ever does that
    return {getattr(s, "identifier", None) or s.name: s.asdict() for s in doc.specifications}


def _ref(key: str, spec: dict) -> dict:
    return {"key": key, "name": spec.get("@name") or key}


def diff_ids(old: ids.Ids, new: ids.Ids) -> dict:
    """Specifications are matched by identifier, else by name. `parts` name what differs in a changed one."""
    a, b = _specs(old), _specs(new)
    changed = [
        {**_ref(k, b[k]), "parts": [p.lstrip("@") for p in PARTS if a[k].get(p) != b[k].get(p)]}
        for k in b
        if k in a and a[k] != b[k]
    ]
    return {
        "added": [_ref(k, b[k]) for k in b if k not in a],
        "removed": [_ref(k, a[k]) for k in a if k not in b],
        "changed": changed,
        "unchanged": sum(1 for k in b if k in a and a[k] == b[k]),
    }
