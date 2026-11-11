"""issue change history

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-11 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issue_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_key", sa.String(40), nullable=False),
        sa.Column("field", sa.String(16), nullable=False),
        sa.Column("old", sa.Text()),
        sa.Column("new", sa.Text()),
        sa.Column("author", sa.String()),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_issue_events_model_id", "issue_events", ["model_id"])
    op.create_index("ix_issue_events_key", "issue_events", ["model_id", "identity_key"])


def downgrade() -> None:
    op.drop_index("ix_issue_events_key", "issue_events")
    op.drop_index("ix_issue_events_model_id", "issue_events")
    op.drop_table("issue_events")
