"""Engine creation and programmatic Alembic migration."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(engine: Engine | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    if engine is not None:
        cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return cfg


def get_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if parsed.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _sqlite_pragmas)
    return engine


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def migrate(engine: Engine) -> None:
    cfg = alembic_config(engine)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
