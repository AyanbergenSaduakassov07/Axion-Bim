"""frozen acceptance certificates

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-11 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_run_id", sa.Integer(), sa.ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_certificates_audit_run_id", "certificates", ["audit_run_id"])


def downgrade() -> None:
    op.drop_index("ix_certificates_audit_run_id", "certificates")
    op.drop_table("certificates")
