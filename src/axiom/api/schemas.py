"""Request/response models for the OpenAPI contract consumed by apps/web (P09)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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


class CopilotQuery(BaseModel):
    project_id: int  # the UI session's project; tools never take a project from the model
    question: str = Field(min_length=1, max_length=2000)


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
