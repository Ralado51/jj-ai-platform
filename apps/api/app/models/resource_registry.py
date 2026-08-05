from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResourceRegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resource_registry"
    __table_args__ = (
        UniqueConstraint("owner_id", "resource_type", "resource_id", name="uq_resource_registry_owner_type_resource"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", server_default="active", index=True)
    resource_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    labels: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False, default=list, server_default="{}")


class ResourceFavorite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resource_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "registry_id", name="uq_resource_favorite_user_registry"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resource_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
