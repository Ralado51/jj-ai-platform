"""add agent workflows

Revision ID: 20260802_04
Revises: 20260801_03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260802_04"
down_revision = "20260801_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_workflows",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("default_instruction", sa.Text(), nullable=True),
        sa.Column("session_key", sa.String(length=120), nullable=True),
        sa.Column("use_memory", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_workflows_user_id", "agent_workflows", ["user_id"])
    op.create_index("ix_agent_workflows_project_id", "agent_workflows", ["project_id"])
    op.create_index("ix_agent_workflows_name", "agent_workflows", ["name"])
    op.create_index("ix_agent_workflows_user_active", "agent_workflows", ["user_id", "is_active"])


def downgrade() -> None:
    op.drop_table("agent_workflows")
