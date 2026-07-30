from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reusable prompt template available globally or inside one project."""

    __tablename__ = "prompt_templates"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="general", server_default="general", index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict, server_default="{}")
