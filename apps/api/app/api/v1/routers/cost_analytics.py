import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.ai_usage_repository import AIUsageRepository
from app.schemas.ai_usage import AIUsageDashboardResponse
from app.services.ai_cost_analytics_service import AICostAnalyticsService

router = APIRouter(prefix="/analytics/usage", tags=["analytics"])


@router.get("/dashboard", response_model=AIUsageDashboardResponse)
def get_ai_usage_dashboard(
    project_id: UUID | None = None,
    agent_id: UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> AIUsageDashboardResponse:
    result = AICostAnalyticsService(AIUsageRepository(db)).dashboard(
        user_id=user.id,
        project_id=project_id,
        agent_id=agent_id,
        provider=provider,
        model=model,
        date_from=date_from,
        date_to=date_to,
    )
    return AIUsageDashboardResponse(**result)
