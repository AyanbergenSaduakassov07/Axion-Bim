"""delivery stage on revisions and gate policy per stage

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-11 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("revisions", sa.Column("stage", sa.String(), nullable=True))
    op.create_table(
        "gate_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("gate_min_score", sa.Float(), nullable=False),
        sa.Column("gate_block_severity", sa.String(), nullable=False),
        sa.Column("gate_require_ids", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("project_id", "stage", name=op.f("uq_gate_policies_project_id")),
    )
    op.create_index("ix_gate_policies_project_id", "gate_policies", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_gate_policies_project_id", "gate_policies")
    op.drop_table("gate_policies")
    with op.batch_alter_table("revisions") as batch:
        batch.drop_column("stage")
