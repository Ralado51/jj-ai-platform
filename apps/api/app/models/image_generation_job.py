from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset


class ImageGenerationJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "image_generation_jobs"

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="free-worker")
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="Z-Image-Turbo")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1344)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    worker_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset | None"] = relationship(foreign_keys=[asset_id], lazy="joined")

    @property
    def asset_url(self) -> str | None:
        return self.asset.public_url if self.asset else None
