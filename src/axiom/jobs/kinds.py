"""Job kinds executed inside the job child process (see services.jobs.KINDS)."""

from __future__ import annotations

from axiom.config import Settings
from axiom.repo.db import get_engine
from axiom.services import audits, comparisons, revisions


def pipeline(payload: dict, settings: Settings) -> dict:
    """Uploaded IFC -> ingest -> audit (built-ins + optional IDS/geometry) -> compare with previous."""
    engine = get_engine(settings.db_url)
    files = settings.files_dir
    ids_hash = payload.get("ids_hash")
    ingested = revisions.ingest(
        engine, payload["model_id"], files / f"{payload['file_sha256']}.ifc", files_dir=files
    )
    audit = audits.run_audit(
        engine,
        ingested.revision_id,
        ids_path=files / f"{ids_hash}.ids" if ids_hash else None,
        files_dir=files,
        geometry=bool(payload.get("geometry")),
    )
    cmp = comparisons.compare_with_previous(engine, ingested.revision_id)
    return {
        "revision_id": ingested.revision_id,
        "seq": ingested.seq,
        "created": ingested.created,
        "audit_run_id": audit.audit_run_id,
        "comparison_id": cmp.comparison_id if cmp else None,
    }


def compare(payload: dict, settings: Settings) -> dict:
    engine = get_engine(settings.db_url)
    r = comparisons.compare(engine, payload["base_revision_id"], payload["head_revision_id"])
    return {"comparison_id": r.comparison_id}
