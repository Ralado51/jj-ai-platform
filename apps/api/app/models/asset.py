from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssetType


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a file or generated artifact associated with a project."""

    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        SQLEnum(AssetType, name="asset_type"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_provider: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="local",
        server_default="local",
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    project: Mapped["Project"] = relationship(back_populates="assets")
    execution: Mapped["Execution | None"] = relationship(back_populates="assets")
