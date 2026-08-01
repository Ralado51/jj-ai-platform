from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.analytics import AIAnalyticsSummaryResponse
from app.services.analytics_service import AnalyticsService
from app.services.model_router import AITaskType

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(BenchmarkRepository(db))


@router.get("/summary", response_model=AIAnalyticsSummaryResponse)
def get_summary(
    task: AITaskType | None = None,
    service: AnalyticsService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> AIAnalyticsSummaryResponse:
    return service.summary(user_id=user.id, task=task)
