"""Finding: the single output schema of custom rules and IDS checks (D-04). Vocabularies per PLAN §3."""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"
    ERROR = "error"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(StrEnum):
    GEOMETRY = "geometry"
    IDENTITY = "identity"
    SPATIAL = "spatial"
    MATERIAL = "material"
    METADATA = "metadata"
    CLASSIFICATION = "classification"
    QUANTITY = "quantity"
    INFORMATION = "information"  # IDS requirements


def identity_key(model_id: int, rule_id: str, global_id: str | None, issue_key: str) -> str:
    """Stable across revisions of one model: same element, same rule, same condition -> same key."""
    raw = f"{model_id}|{rule_id}|{global_id or ''}|{issue_key}"
    return hashlib.sha1(raw.encode()).hexdigest()  # noqa: S324 - identity, not security


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=True)

    identity_key: str
    rule_id: str
    rule_version: str
    status: CheckStatus
    severity: Severity
    category: Category
    dimension: str
    issue_key: str
    global_id: str | None
    step_id: int | None
    ifc_class: str | None
    element_name: str | None
    expected: str | None
    actual: str | None
    message: str
    evidence: dict
