from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MemoryType


class Memory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores searchable project knowledge and its vector embedding."""

    __tablename__ = "memories"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        SQLEnum(MemoryType, name="memory_type"),
        nullable=False,
        default=MemoryType.LONG_TERM,
        server_default=MemoryType.LONG_TERM.value,
        index=True,
    )
    key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )
    importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default="0.5",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    memory_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    project: Mapped["Project"] = relationship(back_populates="memories")
