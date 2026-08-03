"""add notification email deliveries

Revision ID: 20260803_11
Revises: 20260803_10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260803_11"
down_revision = "20260803_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_email_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["agent_workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "deduplication_key", name="uq_notification_email_delivery_user_dedup"),
    )
    op.create_index("ix_notification_email_deliveries_user_id", "notification_email_deliveries", ["user_id"], unique=False)
    op.create_index("ix_notification_email_deliveries_status", "notification_email_deliveries", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_email_deliveries_status", table_name="notification_email_deliveries")
    op.drop_index("ix_notification_email_deliveries_user_id", table_name="notification_email_deliveries")
    op.drop_table("notification_email_deliveries")
