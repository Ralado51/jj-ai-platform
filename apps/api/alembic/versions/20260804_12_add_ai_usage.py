"""add ai usage

Revision ID: 20260804_12
Revises: 20260803_11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260804_12"
down_revision = "20260803_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_step", sa.Integer(), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("task", sa.String(length=80), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_input_cost", sa.Numeric(14, 8), server_default="0", nullable=False),
        sa.Column("estimated_output_cost", sa.Numeric(14, 8), server_default="0", nullable=False),
        sa.Column("estimated_cost", sa.Numeric(14, 8), server_default="0", nullable=False),
        sa.Column("equivalent_openai_cost", sa.Numeric(14, 8), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cached_response", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("request_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "project_id", "workflow_execution_id", "agent_id", "provider", "model", "task", "cached_response"):
        op.create_index(f"ix_ai_usage_{column}", "ai_usage", [column], unique=False)
    op.create_index("ix_ai_usage_user_created", "ai_usage", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("ai_usage")
