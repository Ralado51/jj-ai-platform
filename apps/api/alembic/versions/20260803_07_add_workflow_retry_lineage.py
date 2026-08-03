"""add workflow retry lineage

Revision ID: 20260803_07
Revises: 20260802_06
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260803_07"
down_revision: str | None = "20260802_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_executions",
        sa.Column("parent_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "workflow_executions",
        sa.Column("retry_from_step", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_executions_parent_execution_id",
        "workflow_executions",
        "workflow_executions",
        ["parent_execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workflow_executions_parent_execution_id",
        "workflow_executions",
        ["parent_execution_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_workflow_executions_retry_from_step",
        "workflow_executions",
        "retry_from_step IS NULL OR retry_from_step BETWEEN 1 AND 6",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_workflow_executions_retry_from_step",
        "workflow_executions",
        type_="check",
    )
    op.drop_index(
        "ix_workflow_executions_parent_execution_id",
        table_name="workflow_executions",
    )
    op.drop_constraint(
        "fk_workflow_executions_parent_execution_id",
        "workflow_executions",
        type_="foreignkey",
    )
    op.drop_column("workflow_executions", "retry_from_step")
    op.drop_column("workflow_executions", "parent_execution_id")
