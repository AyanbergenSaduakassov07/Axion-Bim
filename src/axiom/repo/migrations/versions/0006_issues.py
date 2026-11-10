"""issue triage keyed by finding identity

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-10 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("identity_key", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("assignee", sa.String(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"], ["models.id"], name="fk_issues_model_id_models", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_issues"),
        sa.UniqueConstraint("model_id", "identity_key", name="uq_issues_model_id"),
    )
    op.create_index("ix_issues_model_id", "issues", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_issues_model_id", table_name="issues")
    op.drop_table("issues")
