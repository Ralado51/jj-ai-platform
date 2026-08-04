from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIUsage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_usage"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    task: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_input_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    estimated_output_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    equivalent_openai_cost: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_response: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    request_started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_finished_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
