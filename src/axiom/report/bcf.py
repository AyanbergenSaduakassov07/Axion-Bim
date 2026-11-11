"""BCF 3.0 and 2.1 export of open findings via IfcOpenShell's bcf-client (models from the official XSDs).

2.1 exists for Revit: most Revit BCF add-ins and Autodesk Construction Cloud import 2.1 only. Components carry
the element's IfcElement.Tag as AuthoringToolId (Revit writes its ElementId there) next to the IfcGuid.

One topic per fail/warning finding. Topic GUIDs derive from the finding identity_key, so re-exporting a later
audit updates the same topics in a BCF tool instead of duplicating them. Viewpoints select the element by
GlobalId. BCF 3.0 requires a camera: it looks at the element's placement origin (stored at extraction)
from a fixed offset, or gives an overview of the model origin when the element has no placement.
"""

from __future__ import annotations

import datetime
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import numpy as np
from bcf import v2, v3
from bcf.geometry import camera_vectors_from_target_position
from bcf.v2 import bcfxml as bcfxml2
from bcf.v2 import topic as topic2
from bcf.v2 import visinfo as visinfo2
from bcf.v3 import bcfxml as bcfxml3
from bcf.v3 import model as mdl
from bcf.v3 import topic as topic3
from bcf.v3 import visinfo as visinfo3
from xsdata.models.datatype import XmlDateTime

OPEN = frozenset({"fail", "warning"})
NAMESPACE = uuid.UUID("6f7d2c1e-3b4a-4f0e-9a8b-41c0f1e2d3a4")  # fixed: same finding -> same topic GUID
AUTHOR = "Axiom BIM"
BCF_STATUS = {
    "open": "Open",
    "in_progress": "In Progress",
    "disputed": "Disputed",
    "accepted": "Accepted",
    "closed": "Closed",
}
FIELD_LABEL = {"state": "State", "assignee": "Assignee", "due_date": "Due date", "note": "Note"}
OVERVIEW_OFFSET_M = np.array((30.0, 30.0, 30.0))
CLOSE_UP_OFFSET_M = np.array((6.0, -8.0, 5.0))  # ~11 m away, from the south-east, above


@dataclass(frozen=True)
class _Api:
    version: str
    mdl: ModuleType
    bcfxml: ModuleType
    topic: ModuleType
    visinfo: ModuleType


APIS = {
    "3.0": _Api("3.0", v3.model, bcfxml3, topic3, visinfo3),
    "2.1": _Api("2.1", v2.model, bcfxml2, topic2, visinfo2),
}


def topic_guid(identity_key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, identity_key))


def to_bcf(report: dict, version: str = "3.0") -> bytes:
    api = APIS[version]
    revision = report["audit"]["revision"]
    bcf = api.bcfxml.BcfXml.create_new(project_name=revision.get("project_name") or "Axiom BIM")
    now = XmlDateTime.from_datetime(datetime.datetime.now(datetime.UTC))
    for f in report["findings"]:
        if f["status"] in OPEN:
            handler = _topic(api, f, now, report["audit"]["id"])
            bcf.topics[handler.guid] = handler
    if version == "3.0":  # 2.1 declares extensions as an XSD file; tools accept topics without one
        bcf.extensions = _extensions([h.topic for h in bcf.topics.values()])
    with tempfile.TemporaryDirectory() as tmp:  # bcf-client saves to a path only
        path = Path(tmp) / "audit.bcf"
        bcf.save(path)
        return path.read_bytes()


def _extensions(topics: list[mdl.Topic]) -> mdl.Extensions:
    """BCF 3.0 tools may reject values not declared here; list all five statuses so replies can use any."""

    def used(values) -> list[str]:
        return sorted({v for v in values if v})

    return mdl.Extensions(
        topic_types=mdl.ExtensionsTopicTypes(topic_type=used(t.topic_type for t in topics)),
        topic_statuses=mdl.ExtensionsTopicStatuses(topic_status=list(BCF_STATUS.values())),
        priorities=mdl.ExtensionsPriorities(priority=used(t.priority for t in topics)),
        topic_labels=mdl.ExtensionsTopicLabels(
            topic_label=used(lb for t in topics if t.labels for lb in t.labels.label)
        ),
        users=mdl.ExtensionsUsers(user=used(t.assigned_to for t in topics)),
    )


def _topic(api: _Api, f: dict, now: XmlDateTime, audit_id: int):
    guid = topic_guid(f["identity_key"])
    element = f["element_name"] or f["global_id"] or "project"
    issue = f.get("issue") or {}
    due = issue.get("due_date")
    m = api.mdl
    comments = _comments(m, f.get("history") or [], issue.get("note"), guid, now)
    labels = [f["rule_id"], f["dimension"] or f["category"] or "other"]
    common = dict(
        guid=guid,
        title=f"{f['rule_id']} · {element}: {f['message']}"[:250],
        description=_description(f, audit_id),
        topic_type="Information deficiency" if f["status"] == "fail" else "Warning",
        topic_status=BCF_STATUS[issue.get("state") or "open"],
        assigned_to=issue.get("assignee"),
        due_date=XmlDateTime.from_string(f"{due}T00:00:00Z") if due else None,
        priority=f["severity"],
        creation_date=now,
        creation_author=AUTHOR,
    )
    handler = api.topic.TopicHandler(topic_dir=Path(guid))
    if api.version == "3.0":  # 3.0 nests labels and comments in the topic; 2.1 keeps comments in the markup
        thread = m.TopicComments(comment=comments) if comments else None
        topic = m.Topic(**common, labels=m.TopicLabels(label=labels), comments=thread)
        handler.markup = m.Markup(topic=topic)
    else:
        handler.markup = m.Markup(topic=m.Topic(**common, labels=labels), comment=comments)
    if f["global_id"]:
        vi = m.VisualizationInfo(
            guid=str(uuid.uuid4()),
            components=_components(m, f["global_id"], f.get("authoring_tool_id")),
            perspective_camera=_camera(api, f.get("origin_m")),
        )
        handler.add_visinfo_handler(api.visinfo.VisualizationInfoHandler(visualization_info=vi))
    return handler


def _components(m: ModuleType, global_id: str, tag: str | None):
    component = m.Component(ifc_guid=global_id, authoring_tool_id=tag)
    return m.Components(
        selection=m.ComponentSelection(component=[component]),
        visibility=m.ComponentVisibility(default_visibility=True),
    )


def _comments(m: ModuleType, history: list[dict], note: str | None, topic: str, now: XmlDateTime) -> list:
    """Issue history (D-41) as dated comments by their author, then the current note. GUIDs are stable."""
    out = [
        m.Comment(
            guid=str(uuid.uuid5(NAMESPACE, f"{topic}:event:{i}")),
            date=XmlDateTime.from_datetime(_aware(e["at"])),
            author=e["author"] or AUTHOR,
            comment=f"{FIELD_LABEL[e['field']]}: {_shown(e['field'], e['old'])} → "
            f"{_shown(e['field'], e['new'])}",
        )
        for i, e in enumerate(history)
    ]
    if note:
        out.append(
            m.Comment(guid=str(uuid.uuid5(NAMESPACE, f"{topic}:note")), date=now, author=AUTHOR, comment=note)
        )
    return out


def _shown(field: str, value: str | None) -> str:
    if not value:
        return "—"
    return BCF_STATUS.get(value, value) if field == "state" else value


def _aware(at: datetime.datetime | str) -> datetime.datetime:
    at = datetime.datetime.fromisoformat(at) if isinstance(at, str) else at
    return at if at.tzinfo else at.replace(tzinfo=datetime.UTC)  # SQLite returns naive UTC


def _camera(api: _Api, origin: list[float] | None):
    target, offset = (np.array(origin), CLOSE_UP_OFFSET_M) if origin else (np.zeros(3), OVERVIEW_OFFSET_M)
    return api.visinfo.build_camera_from_vectors(*camera_vectors_from_target_position(target, offset))


def _description(f: dict, audit_id: int) -> str:
    return (
        f"{f['message']}\nExpected: {f['expected'] or '-'}\nActual: {f['actual'] or '-'}\n"
        f"Element: {f['ifc_class'] or '-'} {f['global_id'] or '(project level)'}\n"
        f"Rule {f['rule_id']} v{f['rule_version']} · severity {f['severity']} · Axiom audit {audit_id} · "
        f"finding {f['identity_key']}"
    )
