from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents an AI agent configured inside a project."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_agents_project_slug"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="openai",
        server_default="openai",
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    project: Mapped["Project"] = relationship(back_populates="agents")
    tasks: Mapped[list["Task"]] = relationship(back_populates="agent")
    executions: Mapped[list["Execution"]] = relationship(back_populates="agent")
