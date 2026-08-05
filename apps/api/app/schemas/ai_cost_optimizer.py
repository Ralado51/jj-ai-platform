from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RecommendationStatus = Literal["open", "in_review", "applied", "ignored"]


class AICostRecommendationResponse(BaseModel):
    id: str
    priority: Literal["high", "medium", "low"]
    category: str
    title: str
    description: str
    action: str
    estimated_monthly_savings: Decimal
    confidence: float
    evidence: dict[str, Any]


class AICostOptimizerResponse(BaseModel):
    potential_monthly_savings: Decimal
    recommendations: list[AICostRecommendationResponse]


class AICostRecommendationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_key: str
    priority: str
    category: str
    title: str
    description: str
    action: str
    estimated_monthly_savings: Decimal
    confidence: float
    evidence: dict[str, Any]
    status: RecommendationStatus
    notes: str | None
    first_seen_at: dt.datetime
    last_seen_at: dt.datetime
    resolved_at: dt.datetime | None


class AICostRecommendationStatusRequest(BaseModel):
    status: RecommendationStatus
    notes: str | None = None
