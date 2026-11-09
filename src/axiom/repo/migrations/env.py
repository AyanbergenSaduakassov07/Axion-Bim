"""Alembic env: online only. Uses the connection passed by axiom.repo.db.migrate, else sqlalchemy.url."""

from alembic import context
from sqlalchemy import create_engine

from axiom.repo.tables import metadata

config = context.config


def _run(connection) -> None:
    # render_as_batch: SQLite cannot ALTER most constraints in place
    context.configure(connection=connection, target_metadata=metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if (conn := config.attributes.get("connection")) is not None:
    _run(conn)
else:
    with create_engine(config.get_main_option("sqlalchemy.url")).connect() as c:
        _run(c)
