"""add ai cost recommendations

Revision ID: 20260805_13
Revises: 20260804_12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_13"
down_revision = "20260804_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_cost_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_key", sa.String(length=180), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("estimated_monthly_savings", sa.Numeric(14, 6), server_default="0", nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), server_default="0", nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "recommendation_key", name="uq_ai_cost_recommendation_user_key"),
    )
    op.create_index("ix_ai_cost_recommendations_user_id", "ai_cost_recommendations", ["user_id"])
    op.create_index("ix_ai_cost_recommendations_status", "ai_cost_recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("ai_cost_recommendations")
