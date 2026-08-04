import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.ai_usage_repository import AIUsageRepository
from app.schemas.ai_cost_optimizer import AICostOptimizerResponse
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
    return AICostOptimizerResponse(**result)
