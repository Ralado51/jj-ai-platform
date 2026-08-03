from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowHealthHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_health_history"
    __table_args__ = (
        UniqueConstraint("user_id", "workflow_id", "snapshot_date", name="uq_workflow_health_daily"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(150), nullable=False)
    snapshot_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    health_label: Mapped[str] = mapped_column(String(30), nullable=False)
    executions: Mapped[int] = mapped_column(Integer, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    retry_rate: Mapped[float] = mapped_column(Float, nullable=False)
    average_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    bottleneck_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bottleneck_share: Mapped[float | None] = mapped_column(Float, nullable=True)
