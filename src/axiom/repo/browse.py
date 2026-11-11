"""Read-only listing queries for the API (P08)."""

from __future__ import annotations

from sqlalchemy import Connection, Row, func, select

from axiom.repo.tables import (
    audit_runs,
    comparisons,
    elements,
    models,
    projects,
    revision_changes,
    revisions,
    spatial_nodes,
)

ELEMENT_COLS = (
    elements.c.global_id,
    elements.c.step_id,
    elements.c.ifc_class,
    elements.c.name,
    elements.c.storey_global_id,
    elements.c.has_geometry,
)
REVISION_COLS = (
    revisions.c.id,
    revisions.c.model_id,
    revisions.c.seq,
    revisions.c.file_sha256,
    revisions.c.file_size,
    revisions.c.schema_name,
    revisions.c.status,
    revisions.c.created_at,
)


def list_projects(conn: Connection) -> list[Row]:
    return conn.execute(select(projects).order_by(projects.c.id)).all()


def get_project(conn: Connection, project_id: int) -> Row | None:
    return conn.execute(select(projects).where(projects.c.id == project_id)).first()


def list_models(conn: Connection, project_id: int) -> list[Row]:
    return conn.execute(select(models).where(models.c.project_id == project_id).order_by(models.c.id)).all()


def get_model(conn: Connection, model_id: int) -> Row | None:
    return conn.execute(select(models).where(models.c.id == model_id)).first()


def list_revisions(conn: Connection, model_id: int) -> list[Row]:
    q = select(*REVISION_COLS).where(revisions.c.model_id == model_id).order_by(revisions.c.seq)
    return conn.execute(q).all()


def get_revision(conn: Connection, revision_id: int) -> Row | None:
    return conn.execute(select(revisions).where(revisions.c.id == revision_id)).first()


def class_counts(conn: Connection, revision_id: int) -> dict[str, int]:
    q = (
        select(elements.c.ifc_class, func.count())
        .where(elements.c.revision_id == revision_id)
        .group_by(elements.c.ifc_class)
        .order_by(elements.c.ifc_class)
    )
    return {cls: n for cls, n in conn.execute(q)}


def elements_page(
    conn: Connection, revision_id: int, filters: dict[str, str | None], limit: int, offset: int
) -> tuple[int, list[Row]]:
    where = [elements.c.revision_id == revision_id]
    if filters.get("ifc_class"):
        where.append(elements.c.ifc_class == filters["ifc_class"])
    if filters.get("storey"):
        where.append(elements.c.storey_global_id == filters["storey"])
    if term := filters.get("search"):
        needle = term.lower()
        where.append(
            func.lower(elements.c.name).contains(needle, autoescape=True)
            | func.lower(elements.c.global_id).contains(needle, autoescape=True)
        )
    total = conn.execute(select(func.count()).select_from(elements).where(*where)).scalar_one()
    q = select(*ELEMENT_COLS).where(*where).order_by(elements.c.id).limit(limit).offset(offset)
    return total, conn.execute(q).all()


def spatial_tree(conn: Connection, revision_id: int) -> tuple[list[Row], list[Row]]:
    n = spatial_nodes.c
    nodes = select(n.global_id, n.ifc_class, n.name, n.parent_global_id, n.elevation_m)
    e = elements.c
    els = select(e.global_id, e.step_id, e.ifc_class, e.name, e.container_global_id, e.has_geometry)
    return (
        conn.execute(nodes.where(n.revision_id == revision_id).order_by(n.id)).all(),
        conn.execute(els.where(e.revision_id == revision_id).order_by(e.id)).all(),
    )


def storeys(conn: Connection, revision_id: int) -> list[Row]:
    n = spatial_nodes.c
    q = select(n.name, n.elevation_m).where(n.revision_id == revision_id, n.ifc_class == "IfcBuildingStorey")
    return conn.execute(q.order_by(n.id)).all()


def list_audits(conn: Connection, revision_id: int) -> list[Row]:
    q = select(audit_runs).where(audit_runs.c.revision_id == revision_id).order_by(audit_runs.c.id)
    return conn.execute(q).all()


def get_audit(conn: Connection, audit_run_id: int) -> Row | None:
    return conn.execute(select(audit_runs).where(audit_runs.c.id == audit_run_id)).first()


def list_comparisons(conn: Connection, revision_id: int) -> list[Row]:
    q = select(comparisons).where(
        (comparisons.c.head_revision_id == revision_id) | (comparisons.c.base_revision_id == revision_id)
    )
    return conn.execute(q.order_by(comparisons.c.id)).all()


def get_comparison(conn: Connection, comparison_id: int) -> Row | None:
    return conn.execute(select(comparisons).where(comparisons.c.id == comparison_id)).first()


def list_changes(conn: Connection, comparison_id: int) -> list[Row]:
    q = select(revision_changes).where(revision_changes.c.comparison_id == comparison_id)
    return conn.execute(q.order_by(revision_changes.c.id)).all()


def latest_comparison_for_audit(conn: Connection, audit_run_id: int) -> Row | None:
    q = select(comparisons).where(comparisons.c.head_audit_run_id == audit_run_id)
    return conn.execute(q.order_by(comparisons.c.id.desc())).first()


def element_origins(conn: Connection, revision_id: int) -> dict[int, tuple[float, float, float]]:
    """step_id -> world placement origin in metres, for elements that have one."""
    e = elements.c
    rows = conn.execute(
        select(e.step_id, e.origin_x, e.origin_y, e.origin_z).where(
            e.revision_id == revision_id, e.origin_x.is_not(None)
        )
    )
    return {r.step_id: (r.origin_x, r.origin_y, r.origin_z) for r in rows}
