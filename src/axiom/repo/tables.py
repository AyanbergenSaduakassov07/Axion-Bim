"""SQLAlchemy Core schema (PLAN §3 core entities). Alembic migrations are generated from this metadata."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def _id() -> Column:
    return Column("id", Integer, primary_key=True)


def _fk(name: str, target: str) -> Column:
    return Column(name, Integer, ForeignKey(f"{target}.id", ondelete="CASCADE"), nullable=False, index=True)


def _created() -> Column:
    return Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False)


projects = Table("projects", metadata, _id(), Column("name", String, nullable=False, unique=True), _created())

models = Table(
    "models",
    metadata,
    _id(),
    _fk("project_id", "projects"),
    Column("name", String, nullable=False),
    _created(),
    UniqueConstraint("project_id", "name"),
)

revisions = Table(
    "revisions",
    metadata,
    _id(),
    _fk("model_id", "models"),
    Column("seq", Integer, nullable=False),  # 1-based order within the model
    Column("file_sha256", String(64), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("schema_name", String, nullable=False),
    Column("length_scale", Float, nullable=False),
    Column("status", String, nullable=False),
    Column("metadata_json", JSON, nullable=False),  # full RevisionMeta
    _created(),
    UniqueConstraint("model_id", "file_sha256"),
    UniqueConstraint("model_id", "seq"),
)

spatial_nodes = Table(
    "spatial_nodes",
    metadata,
    _id(),
    _fk("revision_id", "revisions"),
    Column("global_id", String(22), nullable=False),
    Column("ifc_class", String, nullable=False),
    Column("name", String),
    Column("parent_global_id", String(22)),
    Column("elevation_m", Float),
)

elements = Table(
    "elements",
    metadata,
    _id(),
    _fk("revision_id", "revisions"),
    Column("global_id", String(22), nullable=False),
    Column("step_id", Integer, nullable=False),
    Column("ifc_class", String, nullable=False),
    Column("name", String),
    Column("description", Text),
    Column("object_type", String),
    Column("predefined_type", String),
    Column("container_global_id", String(22)),
    Column("storey_global_id", String(22)),
    Column("parent_global_id", String(22)),
    Column("has_geometry", Boolean, nullable=False),
    Column("representation_types", String, nullable=False),  # comma-joined, e.g. "SweptSolid,Axis"
    Column("origin_x", Float),  # world placement origin, metres (NULL: no placement / pre-0005)
    Column("origin_y", Float),
    Column("origin_z", Float),
    Index("ix_elements_revision_global", "revision_id", "global_id"),
)

property_values = Table(
    "property_values",
    metadata,
    _id(),
    _fk("element_id", "elements"),
    Column("pset", String, nullable=False),
    Column("name", String, nullable=False),
    Column("value_type", String(8), nullable=False),  # str | int | float | bool | null
    Column("value_text", Text),
    Column("value_num", Float),
    Column("unit", String),
)

quantities = Table(
    "quantities",
    metadata,
    _id(),
    _fk("element_id", "elements"),
    Column("qto", String, nullable=False),
    Column("name", String, nullable=False),
    Column("value", Float, nullable=False),
    Column("unit", String),
    Column("si_value", Float, nullable=False),
    Column("method", String(16), nullable=False),
)

material_assocs = Table(
    "material_assocs",
    metadata,
    _id(),
    _fk("element_id", "elements"),
    Column("name", String, nullable=False),
    Column("kind", String, nullable=False),
)

classifications = Table(
    "classifications",
    metadata,
    _id(),
    _fk("element_id", "elements"),
    Column("system", String),
    Column("identification", String),
    Column("name", String),
)

audit_runs = Table(
    "audit_runs",
    metadata,
    _id(),
    _fk("revision_id", "revisions"),
    Column("ruleset_version", String(16), nullable=False),
    Column("ids_hash", String(64)),
    Column("engine_version", String, nullable=False),
    Column("status", String, nullable=False),
    Column("summary_json", JSON, nullable=False),  # per-rule status counts + rule metadata (MHI coverage)
    Column("scoring_config_json", JSON),
    _created(),
)

findings = Table(
    "findings",
    metadata,
    _id(),
    _fk("audit_run_id", "audit_runs"),
    Column("identity_key", String(40), nullable=False, index=True),
    Column("rule_id", String, nullable=False),
    Column("rule_version", String, nullable=False),
    Column("status", String(16), nullable=False),
    Column("severity", String(8), nullable=False),
    Column("category", String, nullable=False),
    Column("dimension", String, nullable=False),
    Column("issue_key", String, nullable=False),
    Column("global_id", String(22)),
    Column("step_id", Integer),
    Column("ifc_class", String),
    Column("element_name", String),
    Column("expected", Text),
    Column("actual", Text),
    Column("message", Text, nullable=False),
    Column("evidence_json", JSON, nullable=False),
)

comparisons = Table(
    "comparisons",
    metadata,
    _id(),
    _fk("base_revision_id", "revisions"),
    _fk("head_revision_id", "revisions"),
    Column("base_audit_run_id", Integer, ForeignKey("audit_runs.id", ondelete="SET NULL")),
    Column("head_audit_run_id", Integer, ForeignKey("audit_runs.id", ondelete="SET NULL")),
    Column("identity_unstable", Boolean, nullable=False),
    Column("summary_json", JSON, nullable=False),  # change/event counts, MHI delta, ids-hash mismatch
    _created(),
)

revision_changes = Table(
    "revision_changes",
    metadata,
    _id(),
    _fk("comparison_id", "comparisons"),
    Column("kind", String(8), nullable=False),  # added | removed | modified
    Column("global_id", String(22), nullable=False),
    Column("ifc_class", String, nullable=False),
    Column("path", String),
    Column("old_json", JSON),
    Column("new_json", JSON),
)

finding_events = Table(
    "finding_events",
    metadata,
    _id(),
    _fk("comparison_id", "comparisons"),
    Column(
        "event", String(10), nullable=False
    ),  # new | resolved | persistent | recurring | changed | uncertain
    Column("identity_key", String(40), nullable=False, index=True),
    Column("rule_id", String, nullable=False),
    Column("global_id", String(22)),
    Column("element_name", String),
    Column("severity", String(8), nullable=False),
    Column("note", String),
)

jobs = Table(
    "jobs",
    metadata,
    _id(),
    Column("kind", String, nullable=False),
    Column("payload_json", JSON, nullable=False),
    Column("status", String(16), nullable=False, index=True),  # queued | running | done | error
    Column("progress", Float, nullable=False, default=0.0),
    Column("result_json", JSON),
    Column("error_message", Text),  # user-safe; full detail goes to the server log only
    _created(),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
)
