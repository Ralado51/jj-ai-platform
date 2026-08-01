from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BenchmarkRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "benchmark_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    winner: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    models: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class BenchmarkResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "benchmark_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
