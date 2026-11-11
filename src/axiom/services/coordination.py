"""Project-level view over the latest delivery of every model: gate decision + cross-model checks (D-39)."""

from __future__ import annotations

from sqlalchemy import Connection, Engine

from axiom.coordination import ModelFacts, check, worst_decision
from axiom.repo import browse as repo
from axiom.repo import comparisons as cmp_repo
from axiom.services import gate


def _latest(conn: Connection, model) -> tuple[dict, ModelFacts | None]:
    revs = repo.list_revisions(conn, model.id)
    row = {"model_id": model.id, "name": model.name, "revision_id": None, "seq": None, "decision": None}
    if not revs:
        return row, None
    rev = revs[-1]
    audit = cmp_repo.latest_audit(conn, rev.id)
    decision = gate.for_audit(conn, audit)["decision"] if audit else None
    meta = repo.get_revision(conn, rev.id).metadata_json
    storeys = tuple((s.name, s.elevation_m) for s in repo.storeys(conn, rev.id))
    facts = ModelFacts(model.name, meta["units"].get("LENGTHUNIT"), meta.get("georef"), storeys)
    return {**row, "revision_id": rev.id, "seq": rev.seq, "decision": decision}, facts


def project_coordination(engine: Engine, project_id: int) -> dict:
    with engine.connect() as conn:
        if repo.get_project(conn, project_id) is None:
            raise LookupError(f"project {project_id} not found")
        pairs = [_latest(conn, m) for m in repo.list_models(conn, project_id)]
    models = [row for row, _ in pairs]
    return {
        "project_id": project_id,
        "decision": worst_decision([m["decision"] for m in models]),
        "models": models,
        "checks": check([facts for _, facts in pairs if facts is not None]),
    }
