import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.ai_usage_repository import AIUsageRepository
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.schemas.ai_usage import AIUsageRecordRequest, AIUsageSummaryResponse
from app.schemas.analytics import AIAnalyticsSummaryResponse, WorkflowAnalyticsResponse, WorkflowHealthHistoryListResponse, WorkflowHealthHistoryResponse, WorkflowHealthRegressionsResponse, WorkflowInsightsResponse
from app.services.ai_usage_service import AIUsageService, UsageMeasurement
from app.services.analytics_service import AnalyticsService
from app.services.model_router import AITaskType
from app.services.workflow_analytics_service import WorkflowAnalyticsService
from app.services.workflow_health_regression_service import WorkflowHealthRegressionService
from app.services.workflow_insights_service import WorkflowInsightsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(BenchmarkRepository(db))


def get_ai_usage_repository(db: Session = Depends(get_db)) -> AIUsageRepository:
    return AIUsageRepository(db)


def get_workflow_service(db: Session = Depends(get_db)) -> WorkflowAnalyticsService:
    return WorkflowAnalyticsService(WorkflowExecutionRepository(db))


def get_workflow_insights_service(db: Session = Depends(get_db)) -> WorkflowInsightsService:
    return WorkflowInsightsService(WorkflowExecutionRepository(db))


def get_workflow_health_repository(db: Session = Depends(get_db)) -> WorkflowHealthHistoryRepository:
    return WorkflowHealthHistoryRepository(db)


@router.get("/summary", response_model=AIAnalyticsSummaryResponse)
def get_summary(task: AITaskType | None = None, service: AnalyticsService = Depends(get_service), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> AIAnalyticsSummaryResponse:
    return service.summary(user_id=user.id, task=task)


@router.get("/usage", response_model=AIUsageSummaryResponse)
def get_ai_usage(project_id: UUID | None = None, agent_id: UUID | None = None, provider: str | None = None, model: str | None = None, date_from: dt.datetime | None = None, date_to: dt.datetime | None = None, repository: AIUsageRepository = Depends(get_ai_usage_repository), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> AIUsageSummaryResponse:
    return AIUsageSummaryResponse(**repository.summary(user_id=user.id, project_id=project_id, agent_id=agent_id, provider=provider, model=model, date_from=date_from, date_to=date_to))


@router.post("/usage", status_code=201)
def record_ai_usage(payload: AIUsageRecordRequest, repository: AIUsageRepository = Depends(get_ai_usage_repository), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER))) -> dict[str, str]:
    item = AIUsageService(repository).record(UsageMeasurement(user_id=user.id, provider=payload.provider, model=payload.model, prompt_tokens=payload.prompt_tokens, completion_tokens=payload.completion_tokens, latency_ms=payload.latency_ms, started_at=payload.request_started_at, finished_at=payload.request_finished_at, project_id=payload.project_id, workflow_execution_id=payload.workflow_execution_id, workflow_step=payload.workflow_step, agent_id=payload.agent_id, task=payload.task, cached_response=payload.cached_response))
    return {"id": str(item.id)}


@router.get("/workflows", response_model=WorkflowAnalyticsResponse)
def get_workflow_analytics(workflow_id: UUID | None = None, service: WorkflowAnalyticsService = Depends(get_workflow_service), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> WorkflowAnalyticsResponse:
    return service.summary(user_id=user.id, workflow_id=workflow_id)


@router.get("/workflows/insights", response_model=WorkflowInsightsResponse)
def get_workflow_insights(workflow_id: UUID | None = None, service: WorkflowInsightsService = Depends(get_workflow_insights_service), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> WorkflowInsightsResponse:
    return service.insights(user_id=user.id, workflow_id=workflow_id)


@router.post("/workflows/health/snapshot", response_model=list[WorkflowHealthHistoryResponse])
def create_workflow_health_snapshot(workflow_id: UUID | None = None, service: WorkflowInsightsService = Depends(get_workflow_insights_service), repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER))) -> list[WorkflowHealthHistoryResponse]:
    insights = service.insights(user_id=user.id, workflow_id=workflow_id)
    return [repository.upsert(user_id=user.id, insight=item, snapshot_date=dt.date.today()) for item in insights.workflows]


@router.get("/workflows/health/history", response_model=WorkflowHealthHistoryListResponse)
def get_workflow_health_history(workflow_id: UUID | None = None, limit: int = 365, repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> WorkflowHealthHistoryListResponse:
    return WorkflowHealthHistoryListResponse(items=repository.list(user_id=user.id, workflow_id=workflow_id, limit=max(1, min(limit, 1000))))


@router.get("/workflows/health/regressions", response_model=WorkflowHealthRegressionsResponse)
def get_workflow_health_regressions(workflow_id: UUID | None = None, repository: WorkflowHealthHistoryRepository = Depends(get_workflow_health_repository), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))) -> WorkflowHealthRegressionsResponse:
    return WorkflowHealthRegressionService(repository, threshold=max(1, get_settings().workflow_health_regression_threshold)).detect(user_id=user.id, workflow_id=workflow_id)
