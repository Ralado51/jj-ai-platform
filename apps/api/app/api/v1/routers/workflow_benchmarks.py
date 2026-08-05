from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.api.v1.routers.agents import get_service as get_agent_service
from app.api.v1.routers.workflows import get_repository as get_workflow_repository
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.agent_workflow_repository import AgentWorkflowRepository
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.repositories.workflow_benchmark_repository import WorkflowBenchmarkRepository
from app.schemas.workflow_benchmarks import (
    WorkflowBenchmarkCreate,
    WorkflowBenchmarkResponse,
)
from app.services.agent_service import AgentService
from app.services.workflow_benchmark_service import WorkflowBenchmarkService

router = APIRouter(prefix="/workflows", tags=["workflow-benchmarks"])


def get_service(
    db: Session = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
) -> WorkflowBenchmarkService:
    return WorkflowBenchmarkService(
        WorkflowBenchmarkRepository(db),
        ResourceVersionRepository(db),
        agent_service=agent_service,
    )


@router.post(
    "/{workflow_id}/benchmarks",
    response_model=WorkflowBenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_workflow_benchmark(
    workflow_id: UUID,
    payload: WorkflowBenchmarkCreate,
    workflow_repository: AgentWorkflowRepository = Depends(get_workflow_repository),
    service: WorkflowBenchmarkService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> WorkflowBenchmarkResponse:
    workflow = workflow_repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado.",
        )
    return service.run(workflow=workflow, payload=payload, user=user)


@router.get(
    "/{workflow_id}/benchmarks",
    response_model=list[WorkflowBenchmarkResponse],
)
def list_workflow_benchmarks(
    workflow_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    workflow_repository: AgentWorkflowRepository = Depends(get_workflow_repository),
    service: WorkflowBenchmarkService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[WorkflowBenchmarkResponse]:
    workflow = workflow_repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado.",
        )
    items, _ = service.list(
        workflow=workflow,
        user=user,
        offset=offset,
        limit=limit,
    )
    return items
