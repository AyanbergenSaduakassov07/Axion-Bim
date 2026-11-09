"""element placement origin (metres) for BCF viewpoints

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-09 23:59:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
AXES = ("origin_x", "origin_y", "origin_z")


def upgrade() -> None:
    with op.batch_alter_table("elements") as batch:
        for name in AXES:
            batch.add_column(sa.Column(name, sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("elements") as batch:
        for name in AXES:
            batch.drop_column(name)
