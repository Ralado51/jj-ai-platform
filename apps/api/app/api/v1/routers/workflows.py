from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.agent_workflow import AgentWorkflow
from app.models.user import User, UserRole
from app.repositories.agent_workflow_repository import AgentWorkflowRepository
from app.schemas.workflows import WorkflowCreate, WorkflowResponse, WorkflowUpdate

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_repository(db: Session = Depends(get_db)) -> AgentWorkflowRepository:
    return AgentWorkflowRepository(db)


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(
    project_id: UUID | None = None,
    include_inactive: bool = Query(default=False),
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[WorkflowResponse]:
    return repository.list(user_id=user.id, project_id=project_id, active_only=not include_inactive)


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> WorkflowResponse:
    workflow = AgentWorkflow(
        user_id=user.id,
        project_id=payload.project_id,
        name=payload.name.strip(),
        description=payload.description,
        steps=[step.model_dump() for step in payload.steps],
        default_instruction=payload.default_instruction,
        session_key=payload.session_key,
        use_memory=payload.use_memory,
    )
    return repository.create(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: UUID,
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowResponse:
    workflow = repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> WorkflowResponse:
    workflow = repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")
    changes = payload.model_dump(exclude_unset=True)
    if "steps" in changes:
        changes["steps"] = [step.model_dump() for step in payload.steps or []]
    for field, value in changes.items():
        setattr(workflow, field, value)
    return repository.save(workflow)


@router.delete("/{workflow_id}", response_model=WorkflowResponse)
def archive_workflow(
    workflow_id: UUID,
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> WorkflowResponse:
    workflow = repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")
    workflow.is_active = False
    return repository.save(workflow)
