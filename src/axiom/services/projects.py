"""Project and model management."""

from sqlalchemy import Engine

from axiom.repo import projects as repo


def create_project(engine: Engine, name: str) -> int:
    with engine.begin() as conn:
        return repo.insert_project(conn, name)


def create_model(engine: Engine, project_id: int, name: str) -> int:
    with engine.begin() as conn:
        return repo.insert_model(conn, project_id, name)
