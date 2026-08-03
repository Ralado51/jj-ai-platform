"""add workflow health history

Revision ID: 20260803_08
Revises: 20260803_07
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260803_08"
down_revision: str | None = "20260803_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_health_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_name", sa.String(length=150), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("health_label", sa.String(length=30), nullable=False),
        sa.Column("executions", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("retry_rate", sa.Float(), nullable=False),
        sa.Column("average_duration_ms", sa.Integer(), nullable=False),
        sa.Column("bottleneck_step", sa.Integer(), nullable=True),
        sa.Column("bottleneck_share", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["agent_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "workflow_id", "snapshot_date", name="uq_workflow_health_daily"),
    )
    op.create_index("ix_workflow_health_history_user_id", "workflow_health_history", ["user_id"])
    op.create_index("ix_workflow_health_history_workflow_id", "workflow_health_history", ["workflow_id"])
    op.create_index("ix_workflow_health_history_snapshot_date", "workflow_health_history", ["snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_workflow_health_history_snapshot_date", table_name="workflow_health_history")
    op.drop_index("ix_workflow_health_history_workflow_id", table_name="workflow_health_history")
    op.drop_index("ix_workflow_health_history_user_id", table_name="workflow_health_history")
    op.drop_table("workflow_health_history")
