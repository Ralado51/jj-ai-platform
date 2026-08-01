"""add benchmark analytics tables

Revision ID: 20260801_01
Revises: 20260730_03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260801_01"
down_revision = "20260730_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "benchmark_runs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("winner", sa.String(length=150), nullable=True),
        sa.Column("models", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_runs_user_id", "benchmark_runs", ["user_id"])
    op.create_index("ix_benchmark_runs_winner", "benchmark_runs", ["winner"])

    op.create_table(
        "benchmark_results",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(length=150), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("overall", sa.Float(), nullable=True),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_results_run_id", "benchmark_results", ["run_id"])
    op.create_index("ix_benchmark_results_model", "benchmark_results", ["model"])
    op.create_index("ix_benchmark_results_success", "benchmark_results", ["success"])
    op.create_index("ix_benchmark_results_overall", "benchmark_results", ["overall"])


def downgrade() -> None:
    op.drop_table("benchmark_results")
    op.drop_table("benchmark_runs")
