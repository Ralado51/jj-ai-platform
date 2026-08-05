from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_cost_recommendation import AICostRecommendation


class AICostRecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync(self, *, user_id: UUID, recommendations: list[dict]) -> list[AICostRecommendation]:
        now = dt.datetime.now(dt.UTC)
        items: list[AICostRecommendation] = []
        for recommendation in recommendations:
            key = recommendation["id"]
            item = self.db.scalar(select(AICostRecommendation).where(AICostRecommendation.user_id == user_id, AICostRecommendation.recommendation_key == key))
            if item is None:
                item = AICostRecommendation(user_id=user_id, recommendation_key=key, first_seen_at=now, last_seen_at=now)
                self.db.add(item)
            item.priority = recommendation["priority"]
            item.category = recommendation["category"]
            item.title = recommendation["title"]
            item.description = recommendation["description"]
            item.action = recommendation["action"]
            item.estimated_monthly_savings = Decimal(recommendation["estimated_monthly_savings"])
            item.confidence = recommendation["confidence"]
            item.evidence = recommendation["evidence"]
            item.last_seen_at = now
            items.append(item)
        self.db.commit()
        for item in items:
            self.db.refresh(item)
        return items

    def list(self, *, user_id: UUID, status: str | None = None) -> list[AICostRecommendation]:
        query = select(AICostRecommendation).where(AICostRecommendation.user_id == user_id)
        if status:
            query = query.where(AICostRecommendation.status == status)
        return list(self.db.scalars(query.order_by(AICostRecommendation.last_seen_at.desc())).all())

    def update_status(self, *, user_id: UUID, recommendation_id: UUID, status: str, notes: str | None) -> AICostRecommendation | None:
        item = self.db.scalar(select(AICostRecommendation).where(AICostRecommendation.id == recommendation_id, AICostRecommendation.user_id == user_id))
        if item is None:
            return None
        item.status = status
        item.notes = notes
        item.resolved_at = dt.datetime.now(dt.UTC) if status in {"applied", "ignored"} else None
        self.db.commit()
        self.db.refresh(item)
        return item
