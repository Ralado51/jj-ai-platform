"""add ai cost budgets

Revision ID: 20260805_14
Revises: 20260805_13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_14"
down_revision = "20260805_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_cost_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(14, 6), nullable=False),
        sa.Column("warning_threshold_percent", sa.Integer(), server_default="80", nullable=False),
        sa.Column("critical_threshold_percent", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scope_type", "scope_id", name="uq_ai_cost_budget_scope"),
    )
    for column in ("user_id", "scope_type", "scope_id", "is_active"):
        op.create_index(f"ix_ai_cost_budgets_{column}", "ai_cost_budgets", [column], unique=False)


def downgrade() -> None:
    op.drop_table("ai_cost_budgets")
