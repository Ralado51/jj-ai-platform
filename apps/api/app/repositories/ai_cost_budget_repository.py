from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_cost_budget import AICostBudget


class AICostBudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, user_id: UUID) -> list[AICostBudget]:
        return list(self.db.scalars(select(AICostBudget).where(AICostBudget.user_id == user_id).order_by(AICostBudget.created_at.desc())).all())

    def get(self, *, user_id: UUID, budget_id: UUID) -> AICostBudget | None:
        return self.db.scalar(select(AICostBudget).where(AICostBudget.id == budget_id, AICostBudget.user_id == user_id))

    def create(self, *, user_id: UUID, **values) -> AICostBudget:
        item = AICostBudget(user_id=user_id, **values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, *, item: AICostBudget, values: dict) -> AICostBudget:
        for key, value in values.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, *, item: AICostBudget) -> None:
        self.db.delete(item)
        self.db.commit()
