"""add resource engine

Revision ID: 20260805_15
Revises: 20260805_14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_15"
down_revision = "20260805_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(length=40), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("labels", postgresql.ARRAY(sa.String(length=80)), server_default=sa.text("'{}'::varchar[]"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "resource_type", "resource_id", name="uq_resource_registry_owner_type_resource"),
    )
    for column in ("owner_id", "project_id", "resource_type", "resource_id", "name", "status"):
        op.create_index(f"ix_resource_registry_{column}", "resource_registry", [column], unique=False)
    op.create_index("ix_resource_registry_labels_gin", "resource_registry", ["labels"], unique=False, postgresql_using="gin")
    op.create_index("ix_resource_registry_metadata_gin", "resource_registry", ["metadata"], unique=False, postgresql_using="gin")

    op.create_table(
        "resource_favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["registry_id"], ["resource_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "registry_id", name="uq_resource_favorite_user_registry"),
    )
    op.create_index("ix_resource_favorites_user_id", "resource_favorites", ["user_id"], unique=False)
    op.create_index("ix_resource_favorites_registry_id", "resource_favorites", ["registry_id"], unique=False)


def downgrade() -> None:
    op.drop_table("resource_favorites")
    op.drop_table("resource_registry")
