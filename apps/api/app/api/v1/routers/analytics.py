import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.schemas.analytics import (
    AIAnalyticsSummaryResponse,
    WorkflowAnalyticsResponse,
    WorkflowHealthHistoryListResponse,
    WorkflowHealthHistoryResponse,
    WorkflowHealthRegressionsResponse,
    WorkflowInsightsResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.model_router import AITaskType
from app.services.workflow_analytics_service import WorkflowAnalyticsService
from app.services.workflow_health_regression_service import WorkflowHealthRegressionService
from app.services.workflow_insights_service import WorkflowInsightsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(BenchmarkRepository(db))


def get_workflow_service(db: Session = Depends(get_db)) -> WorkflowAnalyticsService:
    return WorkflowAnalyticsService(WorkflowExecutionRepository(db))


def get_workflow_insights_service(db: Session = Depends(get_db)) -> WorkflowInsightsService:
    return WorkflowInsightsService(WorkflowExecutionRepository(db))


def get_workflow_health_repository(db: Session = Depends(get_db)) -> WorkflowHealthHistoryRepository:
    return WorkflowHealthHistoryRepository(db)


@router.get("/summary", response_model=AIAnalyticsSummaryResponse)
def get_summary(
    task: AITaskType | None = None,
    service: AnalyticsService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> AIAnalyticsSummaryResponse:
    return service.summary(user_id=user.id, task=task)


@router.get("/workflows", response_model=WorkflowAnalyticsResponse)
def get_workflow_analytics(
    workflow_id: UUID | None = None,
    service: WorkflowAnalyticsService = Depends(get_workflow_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowAnalyticsResponse:
    return service.summary(user_id=user.id, workflow_id=workflow_id)


@router.get("/workflows/insights", response_model=WorkflowInsightsResponse)
def get_workflow_insights(
    workflow_id: UUID | None = None,
    service: WorkflowInsightsService = Depends(get_workflow_insights_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowInsightsResponse:
    return service.insights(user_id=user.id, workflow_id=workflow_id)


@router.post("/workflows/health/snapshot", response_model=list[WorkflowHealthHistoryResponse])
def create_workflow_health_snapshot(
    workflow_id: UUID | None = None,
    service: WorkflowInsightsService = Depends(get_workflow_insights_service),
    repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> list[WorkflowHealthHistoryResponse]:
    insights = service.insights(user_id=user.id, workflow_id=workflow_id)
    today = dt.date.today()
    return [repository.upsert(user_id=user.id, insight=item, snapshot_date=today) for item in insights.workflows]


@router.get("/workflows/health/history", response_model=WorkflowHealthHistoryListResponse)
def get_workflow_health_history(
    workflow_id: UUID | None = None,
    limit: int = 365,
    repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowHealthHistoryListResponse:
    safe_limit = max(1, min(limit, 1000))
    return WorkflowHealthHistoryListResponse(items=repository.list(user_id=user.id, workflow_id=workflow_id, limit=safe_limit))


@router.get("/workflows/health/regressions", response_model=WorkflowHealthRegressionsResponse)
def get_workflow_health_regressions(
    workflow_id: UUID | None = None,
    repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowHealthRegressionsResponse:
    threshold = max(1, get_settings().workflow_health_regression_threshold)
    return WorkflowHealthRegressionService(repository, threshold=threshold).detect(
        user_id=user.id,
        workflow_id=workflow_id,
    )
