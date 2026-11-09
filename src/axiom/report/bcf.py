"""BCF 3.0 export of open findings via IfcOpenShell's bcf-client (models generated from the official XSDs).

One topic per fail/warning finding. Topic GUIDs derive from the finding identity_key, so re-exporting a later
audit updates the same topics in a BCF tool instead of duplicating them. Viewpoints select the element by
GlobalId. BCF 3.0 requires a camera: it looks at the element's placement origin (stored at extraction) from a fixed
offset, or gives an overview of the model origin when the element has no placement.
"""

from __future__ import annotations

import datetime
import tempfile
import uuid
from pathlib import Path

import numpy as np
from bcf.geometry import camera_vectors_from_target_position
from bcf.v3 import model as mdl
from bcf.v3.bcfxml import BcfXml
from bcf.v3.topic import TopicHandler
from bcf.v3.visinfo import VisualizationInfoHandler, build_camera_from_vectors, build_components
from xsdata.models.datatype import XmlDateTime

OPEN = frozenset({"fail", "warning"})
NAMESPACE = uuid.UUID("6f7d2c1e-3b4a-4f0e-9a8b-41c0f1e2d3a4")  # fixed: same finding -> same topic GUID
AUTHOR = "Axiom BIM"
OVERVIEW_OFFSET_M = np.array((30.0, 30.0, 30.0))
CLOSE_UP_OFFSET_M = np.array((6.0, -8.0, 5.0))  # ~11 m away, from the south-east, above


def topic_guid(identity_key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, identity_key))


def to_bcf(report: dict) -> bytes:
    revision = report["audit"]["revision"]
    bcf = BcfXml.create_new(project_name=revision.get("project_name") or "Axiom BIM")
    now = XmlDateTime.from_datetime(datetime.datetime.now(datetime.UTC))
    for f in report["findings"]:
        if f["status"] in OPEN:
            handler = _topic(f, now, report["audit"]["id"])
            bcf.topics[handler.guid] = handler
    with tempfile.TemporaryDirectory() as tmp:  # bcf-client saves to a path only
        path = Path(tmp) / "audit.bcf"
        bcf.save(path)
        return path.read_bytes()


def _topic(f: dict, now: XmlDateTime, audit_id: int) -> TopicHandler:
    guid = topic_guid(f["identity_key"])
    element = f["element_name"] or f["global_id"] or "project"
    topic = mdl.Topic(
        guid=guid,
        title=f"{f['rule_id']} · {element}: {f['message']}"[:250],
        description=_description(f, audit_id),
        topic_type="Information deficiency" if f["status"] == "fail" else "Warning",
        topic_status="Open",
        priority=f["severity"],
        labels=mdl.TopicLabels(label=[f["rule_id"], f["dimension"] or f["category"] or "other"]),
        creation_date=now,
        creation_author=AUTHOR,
    )
    handler = TopicHandler(topic_dir=Path(guid))
    handler.markup = mdl.Markup(topic=topic)
    if f["global_id"]:
        vi = mdl.VisualizationInfo(
            guid=str(uuid.uuid4()),
            components=build_components(f["global_id"]),
            perspective_camera=_camera(f.get("origin_m")),
        )
        handler.add_visinfo_handler(VisualizationInfoHandler(visualization_info=vi))
    return handler


def _camera(origin: list[float] | None) -> mdl.PerspectiveCamera:
    target, offset = (np.array(origin), CLOSE_UP_OFFSET_M) if origin else (np.zeros(3), OVERVIEW_OFFSET_M)
    return build_camera_from_vectors(*camera_vectors_from_target_position(target, offset))


def _description(f: dict, audit_id: int) -> str:
    return (
        f"{f['message']}\nExpected: {f['expected'] or '-'}\nActual: {f['actual'] or '-'}\n"
        f"Element: {f['ifc_class'] or '-'} {f['global_id'] or '(project level)'}\n"
        f"Rule {f['rule_id']} v{f['rule_version']} · severity {f['severity']} · Axiom audit {audit_id} · "
        f"finding {f['identity_key']}"
    )
