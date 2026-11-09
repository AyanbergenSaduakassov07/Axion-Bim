"""/api/v1 routes. Thin: parse, call a service, return. No DB or IFC access here."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import Engine

from axiom.api.schemas import (
    Accepted,
    AuditOut,
    ChangeOut,
    CompareIn,
    ComparisonOut,
    CopilotAnswer,
    CopilotQuery,
    CopilotStatus,
    ElementPage,
    IdsOut,
    JobOut,
    ModelOut,
    NameIn,
    ProjectOut,
    RevisionOut,
    RevisionSummary,
    SpatialTree,
)
from axiom.extract.snapshot import Element
from axiom.findings import Finding
from axiom.quantities import GROUPS
from axiom.report import FORMATS
from axiom.revision import FindingEvent
from axiom.services import browse, copilot, jobs, projects, quantities, reports, uploads

router = APIRouter()
MAX_PAGE = 500


def _engine(request: Request) -> Engine:
    return request.app.state.engine


Db = Annotated[Engine, Depends(_engine)]


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Db) -> list[dict]:
    return browse.list_projects(db)


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(db: Db, body: NameIn) -> dict:
    pid = projects.create_project(db, body.name)
    return next(p for p in browse.list_projects(db) if p["id"] == pid)


@router.get("/projects/{project_id}/models", response_model=list[ModelOut])
def list_models(db: Db, project_id: int) -> list[dict]:
    return browse.list_models(db, project_id)


@router.post("/projects/{project_id}/models", response_model=ModelOut, status_code=201)
def create_model(db: Db, project_id: int, body: NameIn) -> dict:
    browse.list_models(db, project_id)  # 404 for an unknown project
    mid = projects.create_model(db, project_id, body.name)
    return next(m for m in browse.list_models(db, project_id) if m["id"] == mid)


@router.get("/models/{model_id}/revisions", response_model=list[RevisionOut])
def list_revisions(db: Db, model_id: int) -> list[dict]:
    return browse.list_revisions(db, model_id)


@router.post("/models/{model_id}/revisions", response_model=Accepted, status_code=202)
def upload_revision(
    request: Request,
    model_id: int,
    file: Annotated[UploadFile, File()],
    ids_hash: Annotated[str | None, Form()] = None,
    geometry: Annotated[bool, Form()] = False,
) -> dict:
    s = request.app.state
    job_id = uploads.accept_revision(
        s.engine, s.settings, model_id, file.file, file.filename or "",
        ids_hash=ids_hash, geometry=geometry, kinds=s.kinds,
    )  # fmt: skip
    s.wake()
    return {"job_id": job_id}


@router.post("/ids", response_model=IdsOut, status_code=201)
def upload_ids(request: Request, file: Annotated[UploadFile, File()]) -> dict:
    return {"ids_hash": uploads.accept_ids(request.app.state.settings, file.file, file.filename or "")}


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(db: Db, job_id: int) -> dict:
    job = jobs.get_job(db, job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    return job


@router.get("/revisions/{revision_id}", response_model=RevisionSummary)
def revision_summary(db: Db, revision_id: int) -> dict:
    return browse.revision_summary(db, revision_id)


@router.get("/revisions/{revision_id}/file", response_class=FileResponse)
def revision_file(request: Request, revision_id: int) -> FileResponse:
    s = request.app.state
    path = browse.revision_file(s.engine, s.settings.files_dir, revision_id)
    return FileResponse(
        path,
        media_type="application/x-step",
        filename=f"revision-{revision_id}.ifc",
        headers={"cache-control": "private, max-age=31536000, immutable"},  # content-addressed by sha256
    )


@router.get("/revisions/{revision_id}/tree", response_model=SpatialTree)
def spatial_tree(db: Db, revision_id: int) -> dict:
    """Spatial structure + every element's container, for the explorer tree (no IFC processing)."""
    return browse.spatial_tree(db, revision_id)


@router.get("/revisions/{revision_id}/elements", response_model=ElementPage)
def list_elements(
    db: Db,
    revision_id: int,
    *,
    ifc_class: str | None = None,
    storey: str | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    filters = {"ifc_class": ifc_class, "storey": storey, "search": search}
    return browse.elements_page(db, revision_id, filters, limit, offset)


@router.get("/revisions/{revision_id}/elements/{global_id}", response_model=Element)
def get_element(db: Db, revision_id: int, global_id: str) -> Element:
    return browse.get_element(db, revision_id, global_id)


@router.get("/revisions/{revision_id}/audits", response_model=list[AuditOut])
def list_audits(db: Db, revision_id: int) -> list[dict]:
    return browse.list_audits(db, revision_id)


@router.get("/revisions/{revision_id}/quantities")
def get_quantities(db: Db, revision_id: int, by: str = "class", against: int | None = None) -> dict[str, Any]:
    """Qto totals (method=qto). Geometry volumes need IFC processing: use `axiom audit --geometry`."""
    if by not in GROUPS:
        raise ValueError(f"unknown grouping {by!r}; use one of {', '.join(GROUPS)}")
    browse.revision_summary(db, revision_id)  # 404 for an unknown revision
    rows = quantities.report(db, revision_id, by)
    deltas = quantities.delta(db, against, revision_id, by) if against is not None else ()
    return {"rows": [asdict(r) for r in rows], "delta": [asdict(d) for d in deltas]}


@router.get("/revisions/{revision_id}/comparisons", response_model=list[ComparisonOut])
def list_comparisons(db: Db, revision_id: int) -> list[dict]:
    return browse.list_comparisons(db, revision_id)


@router.get("/audits/{audit_id}")
def audit_summary(db: Db, audit_id: int) -> dict[str, Any]:
    return browse.audit_summary(db, audit_id)


@router.get("/audits/{audit_id}/findings", response_model=list[Finding])
def list_findings(
    db: Db,
    audit_id: int,
    *,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    rule: str | None = None,
) -> list[Finding]:
    filters = {"status": status, "severity": severity, "category": category, "rule": rule}
    return browse.findings(db, audit_id, filters)


@router.get("/audits/{audit_id}/health-index")
def health_index(db: Db, audit_id: int) -> dict[str, Any]:
    return browse.health_index(db, audit_id)


@router.post(
    "/audits/{audit_id}/reports",
    response_class=Response,
    responses={200: {"content": {t: {} for t in FORMATS.values()}}},
)
def audit_report(
    db: Db,
    audit_id: int,
    fmt: Annotated[Literal["json", "csv", "html", "bcf"], Query(alias="format")] = "json",
    comparison_id: int | None = None,
) -> Response:
    """Render the audit report (with the comparison headed by this audit, if any). HTML opens inline."""
    body = reports.render(reports.build(db, audit_id, comparison_id), fmt)
    disposition = "inline" if fmt == "html" else "attachment"
    return Response(
        body,
        media_type=FORMATS[fmt],
        headers={"Content-Disposition": f'{disposition}; filename="axiom-audit-{audit_id}.{fmt}"'},
    )


@router.post("/comparisons", response_model=Accepted, status_code=202)
def request_comparison(request: Request, body: CompareIn) -> dict:
    db = request.app.state.engine
    browse.revision_summary(db, body.base_revision_id)
    browse.revision_summary(db, body.head_revision_id)
    return {"job_id": request.app.state.enqueue("compare", body.model_dump())}


@router.get("/comparisons/{comparison_id}", response_model=ComparisonOut)
def get_comparison(db: Db, comparison_id: int) -> dict:
    return browse.comparison(db, comparison_id)


@router.get("/comparisons/{comparison_id}/changes", response_model=list[ChangeOut])
def list_changes(db: Db, comparison_id: int) -> list[dict]:
    return browse.changes(db, comparison_id)


@router.get("/comparisons/{comparison_id}/events", response_model=list[FindingEvent])
def list_events(db: Db, comparison_id: int) -> tuple[FindingEvent, ...]:
    return browse.events(db, comparison_id)


@router.get("/copilot", response_model=CopilotStatus)
def copilot_status() -> dict:
    return copilot.status()


@router.post("/copilot/query", response_model=CopilotAnswer)
def copilot_query(db: Db, body: CopilotQuery) -> dict:
    return copilot.query(db, body.project_id, body.question).as_dict()
