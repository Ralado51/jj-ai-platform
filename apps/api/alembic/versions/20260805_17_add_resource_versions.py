"""add resource versions

Revision ID: 20260805_17
Revises: 20260805_16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_17"
down_revision = "20260805_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(length=40), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_resource_versions_event_id"),
        sa.UniqueConstraint(
            "owner_id", "resource_type", "resource_id", "version_number",
            name="uq_resource_versions_resource_number",
        ),
    )
    for column in ("owner_id", "project_id", "resource_type", "resource_id", "occurred_at"):
        op.create_index(f"ix_resource_versions_{column}", "resource_versions", [column], unique=False)
    op.create_index(
        "ix_resource_versions_resource_lookup",
        "resource_versions",
        ["owner_id", "resource_type", "resource_id", "version_number"],
        unique=False,
    )
    op.create_index(
        "ix_resource_versions_snapshot_gin",
        "resource_versions",
        ["snapshot"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("resource_versions")
