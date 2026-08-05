import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.ai_cost_recommendation_repository import AICostRecommendationRepository
from app.repositories.ai_usage_repository import AIUsageRepository
from app.schemas.ai_cost_optimizer import (
    AICostOptimizerResponse,
    AICostRecommendationHistoryResponse,
    AICostRecommendationStatusRequest,
)
from app.services.ai_cost_optimizer_service import AICostOptimizerService

router = APIRouter(prefix="/analytics/optimizer", tags=["analytics"])


@router.get("/recommendations", response_model=AICostOptimizerResponse)
def get_ai_cost_recommendations(
    project_id: UUID | None = None,
    agent_id: UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> AICostOptimizerResponse:
    result = AICostOptimizerService(AIUsageRepository(db)).recommendations(
        user_id=user.id,
        project_id=project_id,
        agent_id=agent_id,
        provider=provider,
        model=model,
        date_from=date_from,
        date_to=date_to,
    )
    AICostRecommendationRepository(db).sync(user_id=user.id, recommendations=result["recommendations"])
    return AICostOptimizerResponse(**result)


@router.get("/recommendations/history", response_model=list[AICostRecommendationHistoryResponse])
def get_recommendation_history(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[AICostRecommendationHistoryResponse]:
    return AICostRecommendationRepository(db).list(user_id=user.id, status=status)


@router.patch("/recommendations/{recommendation_id}", response_model=AICostRecommendationHistoryResponse)
def update_recommendation_status(
    recommendation_id: UUID,
    payload: AICostRecommendationStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> AICostRecommendationHistoryResponse:
    item = AICostRecommendationRepository(db).update_status(
        user_id=user.id,
        recommendation_id=recommendation_id,
        status=payload.status,
        notes=payload.notes,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return item
