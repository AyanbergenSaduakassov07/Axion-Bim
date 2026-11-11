"""/api/v1 routes. Thin: parse, call a service, return. No DB or IFC access here."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import Engine

from axiom.api.schemas import (
    Accepted,
    AuditOut,
    CertificateIn,
    CertificateOut,
    ChangeOut,
    CompareIn,
    ComparisonOut,
    Coordination,
    CopilotAnswer,
    CopilotQuery,
    CopilotStatus,
    Dashboard,
    DefaultIn,
    ElementPage,
    GateOut,
    GatePolicyIO,
    IdentityKey,
    IdsDiff,
    IdsEntry,
    IdsOut,
    IssueEvent,
    IssueOut,
    IssuesUpdated,
    IssueUpdate,
    JobOut,
    ModelOut,
    NameIn,
    ProjectOut,
    RevisionOut,
    RevisionSummary,
    SpatialTree,
    Stage,
    StageIn,
)
from axiom.extract.snapshot import Element
from axiom.findings import Finding
from axiom.i18n import Lang
from axiom.quantities import GROUPS
from axiom.quantities.export import to_csv
from axiom.report import FORMATS
from axiom.revision import FindingEvent
from axiom.score.gate import GatePolicy
from axiom.services import (
    browse,
    certificates,
    coordination,
    copilot,
    dashboard,
    gate,
    ids_library,
    issues,
    jobs,
    projects,
    quantities,
    reports,
    uploads,
)

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


@router.get("/projects/{project_id}/dashboard", response_model=Dashboard)
def project_dashboard(
    db: Db, project_id: int, tz: Annotated[str | None, Query(max_length=64)] = None
) -> dict:
    """`tz` (IANA name, sent by the browser) decides which day "overdue" is measured against."""
    try:
        today = datetime.now(ZoneInfo(tz)).date() if tz else date.today()
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"unknown timezone {tz!r}") from e
    return dashboard.project_dashboard(db, project_id, today)


@router.post("/audits/{audit_run_id}/certificates", response_model=CertificateOut, status_code=201)
def issue_certificate(db: Db, audit_run_id: int, body: CertificateIn) -> dict:
    """Freeze the current gate decision of this audit with its hashes (D-42)."""
    return certificates.issue(db, audit_run_id, body.issued_by)


@router.get("/audits/{audit_run_id}/certificates", response_model=list[CertificateOut])
def list_certificates(db: Db, audit_run_id: int) -> list[dict]:
    return certificates.list_for_audit(db, audit_run_id)


@router.get("/projects/{project_id}/coordination", response_model=Coordination)
def project_coordination(db: Db, project_id: int) -> dict:
    """Project-level delivery decision and cross-model consistency of the latest revisions (D-39)."""
    return coordination.project_coordination(db, project_id)


@router.get("/projects/{project_id}/gate-policy", response_model=GatePolicyIO)
def get_gate_policy(db: Db, project_id: int, stage: Stage | None = None) -> dict:
    """The stage's policy, or the project default when that stage has none (D-45)."""
    return gate.get_policy(db, project_id, stage)


@router.put("/projects/{project_id}/gate-policy", response_model=GatePolicyIO)
def set_gate_policy(db: Db, project_id: int, body: GatePolicyIO, stage: Stage | None = None) -> dict:
    return gate.set_policy(db, project_id, GatePolicy(**body.model_dump()), stage)


@router.put("/revisions/{revision_id}/stage", response_model=RevisionOut)
def set_revision_stage(db: Db, revision_id: int, body: StageIn) -> dict:
    return gate.set_stage(db, revision_id, body.stage)


@router.get("/models/{model_id}", response_model=ModelOut)
def get_model(db: Db, model_id: int) -> dict:
    return browse.get_model(db, model_id)


@router.get("/models/{model_id}/issues", response_model=list[IssueOut])
def list_issues(db: Db, model_id: int) -> list[dict]:
    return issues.list_issues(db, model_id)


@router.put("/models/{model_id}/issues", response_model=IssuesUpdated)
def update_issues(db: Db, model_id: int, body: IssueUpdate) -> dict:
    return {"updated": issues.update(db, model_id, body.identity_keys, body.changes(), author=body.author)}


@router.get("/models/{model_id}/issues/{identity_key}/history", response_model=list[IssueEvent])
def issue_history(db: Db, model_id: int, identity_key: IdentityKey) -> list[dict]:
    """Every change to one issue, oldest first (D-41)."""
    return issues.history(db, model_id, identity_key)


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


@router.get("/projects/{project_id}/ids", response_model=list[IdsEntry])
def list_project_ids(db: Db, project_id: int) -> list[dict]:
    return ids_library.list_entries(db, project_id)


@router.post("/projects/{project_id}/ids", response_model=IdsEntry, status_code=201)
def add_project_ids(
    request: Request,
    db: Db,
    project_id: int,
    file: Annotated[UploadFile, File()],
    name: Annotated[str, Form(max_length=200)] = "",
) -> dict:
    settings = request.app.state.settings
    return ids_library.add(db, settings, project_id, file.file, filename=file.filename or "", name=name)


@router.put("/projects/{project_id}/ids/{entry_id}/default", response_model=list[IdsEntry])
def set_default_ids(db: Db, project_id: int, entry_id: int, body: DefaultIn) -> list[dict]:
    return ids_library.set_default(db, project_id, entry_id, body.is_default)


@router.get("/projects/{project_id}/ids/{entry_id}/diff", response_model=IdsDiff)
def diff_project_ids(request: Request, db: Db, project_id: int, entry_id: int, against: int) -> dict:
    """Specifications added, removed or changed going from library entry `against` to `entry_id`."""
    return ids_library.diff(db, request.app.state.settings, project_id, entry_id, against)


@router.patch("/projects/{project_id}/ids/{entry_id}", response_model=IdsEntry)
def rename_project_ids(db: Db, project_id: int, entry_id: int, body: NameIn) -> dict:
    return ids_library.rename(db, project_id, entry_id, body.name)


@router.delete("/projects/{project_id}/ids/{entry_id}", status_code=204)
def delete_project_ids(db: Db, project_id: int, entry_id: int) -> None:
    ids_library.remove(db, project_id, entry_id)


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


@router.get("/revisions/{revision_id}/quantities", response_model=None)
def get_quantities(
    request: Request,
    db: Db,
    revision_id: int,
    *,
    by: str = "class",
    against: int | None = None,
    fmt: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> dict[str, Any] | Response:
    """Qto totals (method=qto), plus geometry volumes cached by a geometry audit (method=geometry)."""
    if by not in GROUPS:
        raise ValueError(f"unknown grouping {by!r}; use one of {', '.join(GROUPS)}")
    browse.revision_summary(db, revision_id)  # 404 for an unknown revision
    files = request.app.state.settings.files_dir
    rows = quantities.report(db, revision_id, by, files_dir=files)
    deltas = quantities.delta(db, against, revision_id, by, files_dir=files) if against is not None else ()
    if fmt == "csv":
        name = f"axiom-quantities-r{revision_id}-by-{by}.csv"
        return Response(
            to_csv(rows, deltas),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
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
    lang: Lang = "en",
) -> list[Finding]:
    filters = {"status": status, "severity": severity, "category": category, "rule": rule}
    return browse.findings(db, audit_id, filters, lang)


@router.get("/audits/{audit_id}/gate", response_model=GateOut)
def audit_gate(db: Db, audit_id: int) -> dict:
    """Accept/reject decision for this delivery under the project's gate policy and current waivers."""
    return gate.audit_gate(db, audit_id)


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
    lang: Lang = "en",
) -> Response:
    """Render the audit report (with the comparison headed by this audit, if any). HTML opens inline."""
    body = reports.render(reports.build(db, audit_id, comparison_id), fmt, lang)
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
    return copilot.query(
        db, body.project_id, body.question, [(h.question, h.answer) for h in body.history]
    ).as_dict()
