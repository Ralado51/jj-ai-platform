from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PromptEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_evaluations"

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    prompt_id: Mapped[UUID] = mapped_column(ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(150), nullable=False)
    dataset: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
