"""Project and model management."""

from sqlalchemy import Engine

from axiom.repo import projects as repo


def create_project(engine: Engine, name: str) -> int:
    with engine.begin() as conn:
        return repo.insert_project(conn, name)


def create_model(engine: Engine, project_id: int, name: str) -> int:
    with engine.begin() as conn:
        return repo.insert_model(conn, project_id, name)


def ensure_model(engine: Engine, project_name: str, model_name: str) -> int:
    """Get-or-create, for CLI use where projects are implicit."""
    with engine.begin() as conn:
        if (model_id := repo.find_model(conn, project_name, model_name)) is not None:
            return model_id
        project_id = repo.find_project(conn, project_name) or repo.insert_project(conn, project_name)
        return repo.insert_model(conn, project_id, model_name)
