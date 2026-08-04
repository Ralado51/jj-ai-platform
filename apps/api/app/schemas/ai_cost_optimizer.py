from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel


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
