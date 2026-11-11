"""project acceptance gate policy

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-11 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("gate_min_score", sa.Float(), server_default="80", nullable=False))
    op.add_column(
        "projects", sa.Column("gate_block_severity", sa.String(), server_default="critical", nullable=False)
    )
    op.add_column(
        "projects", sa.Column("gate_require_ids", sa.Boolean(), server_default=sa.true(), nullable=False)
    )


def downgrade() -> None:
    for name in ("gate_require_ids", "gate_block_severity", "gate_min_score"):
        op.drop_column("projects", name)
