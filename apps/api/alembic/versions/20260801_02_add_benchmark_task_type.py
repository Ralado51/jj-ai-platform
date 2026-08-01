"""add benchmark task type

Revision ID: 20260801_02
Revises: 20260801_01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260801_02"
down_revision = "20260801_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "benchmark_runs",
        sa.Column(
            "task_type",
            sa.String(length=50),
            nullable=False,
            server_default="general",
        ),
    )
    op.create_index(
        "ix_benchmark_runs_task_type",
        "benchmark_runs",
        ["task_type"],
    )
    op.create_index(
        "ix_benchmark_runs_user_task",
        "benchmark_runs",
        ["user_id", "task_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_benchmark_runs_user_task", table_name="benchmark_runs")
    op.drop_index("ix_benchmark_runs_task_type", table_name="benchmark_runs")
    op.drop_column("benchmark_runs", "task_type")
