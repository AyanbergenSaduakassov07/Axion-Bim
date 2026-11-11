"""element tag (authoring-tool id, e.g. Revit ElementId) for BCF components

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-11 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("elements") as batch:
        batch.add_column(sa.Column("tag", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("elements") as batch:
        batch.drop_column("tag")
