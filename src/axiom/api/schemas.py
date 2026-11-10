"""Request/response models for the OpenAPI contract consumed by apps/web (P09)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime


class ModelOut(ProjectOut):
    project_id: int


class RevisionOut(BaseModel):
    id: int
    model_id: int
    seq: int
    file_sha256: str
    file_size: int
    schema_name: str
    status: str
    created_at: datetime


class RevisionSummary(BaseModel):
    id: int
    model_id: int
    seq: int
    file_sha256: str
    file_size: int
    status: str
    schema_name: str
    metadata: dict[str, Any]
    class_counts: dict[str, int]
    latest_audit_id: int | None
    model_name: str
    project_id: int
    project_name: str


class Accepted(BaseModel):
    job_id: int


class IdsOut(BaseModel):
    ids_hash: str


class JobOut(BaseModel):
    id: int
    kind: str
    status: str  # queued | running | done | error
    progress: float
    result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ElementRow(BaseModel):
    global_id: str
    step_id: int
    ifc_class: str
    name: str | None
    storey_global_id: str | None
    has_geometry: bool


class SpatialNodeOut(BaseModel):
    global_id: str
    ifc_class: str
    name: str | None
    parent_global_id: str | None
    elevation_m: float | None


class TreeElement(BaseModel):
    global_id: str
    step_id: int
    ifc_class: str
    name: str | None
    container_global_id: str | None
    has_geometry: bool


class SpatialTree(BaseModel):
    nodes: list[SpatialNodeOut]
    elements: list[TreeElement]


class ElementPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ElementRow]


class AuditOut(BaseModel):
    id: int
    revision_id: int
    ruleset_version: str
    ids_hash: str | None
    status: str
    engine_version: str
    created_at: datetime
    score: float | None
    coverage: float | None
    blocked: bool


class ComparisonOut(BaseModel):
    id: int
    base_revision_id: int
    head_revision_id: int
    base_audit_run_id: int | None
    head_audit_run_id: int | None
    identity_unstable: bool
    summary_json: dict[str, Any]
    created_at: datetime


class CompareIn(BaseModel):
    base_revision_id: int
    head_revision_id: int


class ChangeOut(BaseModel):
    kind: str
    global_id: str
    ifc_class: str
    path: str | None
    old: Any
    new: Any


class CopilotStatus(BaseModel):
    available: bool
    model: str


class CopilotExchange(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(max_length=8000)


class CopilotQuery(BaseModel):
    project_id: int  # the UI session's project; tools never take a project from the model
    question: str = Field(min_length=1, max_length=2000)
    # earlier turns of the same chat, oldest first
    history: list[CopilotExchange] = Field(default=[], max_length=10)


class CitationOut(BaseModel):
    type: str  # element | finding
    id: str
    label: str | None
    revision_id: int | None


class ToolCallOut(BaseModel):
    name: str
    input: dict[str, Any]


class CopilotAnswer(BaseModel):
    answer: str
    citations: list[CitationOut]
    tool_calls: list[ToolCallOut]
    unverified: list[str]  # ids the model cited without a tool result; already stripped from `answer`
    stop_reason: str


IdentityKey = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
IssueState = Literal["open", "in_progress", "disputed", "accepted", "closed"]


class IssueOut(BaseModel):
    identity_key: str
    state: IssueState
    assignee: str | None
    due_date: date | None
    note: str | None
    updated_at: datetime


class IssueUpdate(BaseModel):
    """Fields left out stay as they are; an explicit null clears assignee, due date or note."""

    identity_keys: list[IdentityKey] = Field(min_length=1, max_length=20000)
    state: IssueState | None = None
    assignee: str | None = Field(default=None, max_length=120)
    due_date: date | None = None
    note: str | None = Field(default=None, max_length=2000)

    def changes(self) -> dict:
        fields = self.model_dump(include=self.model_fields_set - {"identity_keys"})
        return {k: v for k, v in fields.items() if not (k == "state" and v is None)}


class IssuesUpdated(BaseModel):
    updated: int


class TrendPoint(BaseModel):
    revision_id: int
    seq: int
    created_at: datetime
    score: float | None
    coverage: float | None


class ModelHealth(BaseModel):
    model_id: int
    name: str
    trend: list[TrendPoint]
    findings: int


class AssigneeLoad(BaseModel):
    assignee: str
    active: int
    overdue: int


class RuleLoad(BaseModel):
    rule_id: str
    active: int


class IssueTally(BaseModel):
    states: dict[IssueState, int]
    overdue: int
    unassigned: int
    by_assignee: list[AssigneeLoad]
    by_rule: list[RuleLoad]


class Dashboard(BaseModel):
    project_id: int
    name: str
    models: list[ModelHealth]
    issues: IssueTally
