"""Project/model rows."""

from sqlalchemy import Connection, Row, insert, select, update
from sqlalchemy.dialects.sqlite import insert as upsert

from axiom.repo.tables import gate_policies, models, projects, revisions


def insert_project(conn: Connection, name: str) -> int:
    return conn.execute(insert(projects).returning(projects.c.id), {"name": name}).scalar_one()


def insert_model(conn: Connection, project_id: int, name: str) -> int:
    return conn.execute(
        insert(models).returning(models.c.id), {"project_id": project_id, "name": name}
    ).scalar_one()


def find_model(conn: Connection, project_name: str, model_name: str) -> int | None:
    q = (
        select(models.c.id)
        .join(projects, models.c.project_id == projects.c.id)
        .where(projects.c.name == project_name, models.c.name == model_name)
    )
    return conn.execute(q).scalar_one_or_none()


def find_project(conn: Connection, name: str) -> int | None:
    return conn.execute(select(projects.c.id).where(projects.c.name == name)).scalar_one_or_none()


def set_gate_policy(conn: Connection, project_id: int, values: dict) -> None:
    conn.execute(update(projects).where(projects.c.id == project_id).values(**values))


def stage_policy(conn: Connection, project_id: int, stage: str) -> Row | None:
    g = gate_policies.c
    return conn.execute(select(gate_policies).where(g.project_id == project_id, g.stage == stage)).first()


def set_stage_policy(conn: Connection, project_id: int, stage: str, values: dict) -> None:
    stmt = upsert(gate_policies).values(project_id=project_id, stage=stage, **values)
    conn.execute(stmt.on_conflict_do_update(index_elements=["project_id", "stage"], set_=values))


def set_revision_stage(conn: Connection, revision_id: int, stage: str | None) -> None:
    conn.execute(update(revisions).where(revisions.c.id == revision_id).values(stage=stage))
