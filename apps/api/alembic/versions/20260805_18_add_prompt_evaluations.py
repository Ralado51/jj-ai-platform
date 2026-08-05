"""add prompt evaluations

Revision ID: 20260805_18
Revises: 20260805_17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_18"
down_revision = "20260805_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=150), nullable=False),
        sa.Column("dataset", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompt_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("owner_id", "project_id", "prompt_id", "status", "created_at"):
        op.create_index(f"ix_prompt_evaluations_{column}", "prompt_evaluations", [column], unique=False)


def downgrade() -> None:
    op.drop_table("prompt_evaluations")
