from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AICostBudget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_cost_budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "scope_type", "scope_id", name="uq_ai_cost_budget_scope"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    warning_threshold_percent: Mapped[int] = mapped_column(nullable=False, default=80)
    critical_threshold_percent: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
