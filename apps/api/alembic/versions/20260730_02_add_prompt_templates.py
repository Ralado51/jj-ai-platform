"""add prompt templates

Revision ID: 20260730_02
Revises: 20260730_01
Create Date: 2026-07-30 16:40:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260730_02"
down_revision = "20260730_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), server_default="general", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("is_public", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("metadata", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prompt_templates_project_id"), "prompt_templates", ["project_id"], unique=False)
    op.create_index(op.f("ix_prompt_templates_owner_id"), "prompt_templates", ["owner_id"], unique=False)
    op.create_index(op.f("ix_prompt_templates_name"), "prompt_templates", ["name"], unique=False)
    op.create_index(op.f("ix_prompt_templates_category"), "prompt_templates", ["category"], unique=False)
    op.create_index(op.f("ix_prompt_templates_is_public"), "prompt_templates", ["is_public"], unique=False)
    op.create_index(op.f("ix_prompt_templates_is_favorite"), "prompt_templates", ["is_favorite"], unique=False)
    op.create_index(op.f("ix_prompt_templates_is_active"), "prompt_templates", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_prompt_templates_is_active"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_is_favorite"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_is_public"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_category"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_name"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_owner_id"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_project_id"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
