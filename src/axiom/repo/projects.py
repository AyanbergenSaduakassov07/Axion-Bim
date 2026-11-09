"""Project/model rows."""

from sqlalchemy import Connection, insert

from axiom.repo.tables import models, projects


def insert_project(conn: Connection, name: str) -> int:
    return conn.execute(insert(projects).returning(projects.c.id), {"name": name}).scalar_one()


def insert_model(conn: Connection, project_id: int, name: str) -> int:
    return conn.execute(
        insert(models).returning(models.c.id), {"project_id": project_id, "name": name}
    ).scalar_one()
