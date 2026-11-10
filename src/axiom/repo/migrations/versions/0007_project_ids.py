"""project IDS library

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-10 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_ids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("ids_hash", sa.String(length=64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_project_ids_project_id_projects", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_ids"),
        sa.UniqueConstraint("project_id", "ids_hash", name="uq_project_ids_project_id"),
    )
    op.create_index("ix_project_ids_project_id", "project_ids", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_ids_project_id", table_name="project_ids")
    op.drop_table("project_ids")
