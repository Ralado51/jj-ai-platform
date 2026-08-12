"""add image workers

Revision ID: 20260812_22
Revises: 20260812_21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260812_22"
down_revision = "20260812_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("runtime", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_image_workers_name", "image_workers", ["name"], unique=True)
    op.create_index("ix_image_workers_status", "image_workers", ["status"])


def downgrade() -> None:
    op.drop_table("image_workers")
