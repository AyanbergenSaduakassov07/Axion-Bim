from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from axiom.repo.db import get_engine, migrate
from axiom.repo.tables import metadata


def test_migrations_match_table_definitions(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'm.db'}")
    migrate(engine)
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []
