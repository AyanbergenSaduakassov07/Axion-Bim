"""Project/model rows."""

from sqlalchemy import Connection, insert, select

from axiom.repo.tables import models, projects


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
