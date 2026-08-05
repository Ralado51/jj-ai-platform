from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.api.v1.routers.agents import get_service as get_agent_service
from app.db.dependencies import get_db
from app.events.bus import domain_event_bus
from app.events.types import WorkflowArchived, WorkflowCreated, WorkflowUpdated
from app.models.agent_workflow import AgentWorkflow
from app.models.user import User, UserRole
from app.models.workflow_execution import WorkflowExecution
from app.repositories.agent_workflow_repository import AgentWorkflowRepository
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.schemas.agents import AgentRunResponse
from app.schemas.workflows import (
    WorkflowCreate,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator
from app.services.agent_service import AgentService
from app.services.chat_providers import ChatProviderError

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_repository(db: Session = Depends(get_db)) -> AgentWorkflowRepository:
    return AgentWorkflowRepository(db)


def get_execution_repository(db: Session = Depends(get_db)) -> WorkflowExecutionRepository:
    return WorkflowExecutionRepository(db)


def get_version_repository(db: Session = Depends(get_db)) -> ResourceVersionRepository:
    return ResourceVersionRepository(db)


def workflow_snapshot(workflow: AgentWorkflow) -> dict:
    return {
        "name": workflow.name,
        "description": workflow.description,
        "project_id": workflow.project_id,
        "steps": [dict(step) for step in workflow.steps],
        "default_instruction": workflow.default_instruction,
        "session_key": workflow.session_key,
        "use_memory": workflow.use_memory,
        "is_active": workflow.is_active,
    }


def apply_workflow_update(
    *,
    workflow: AgentWorkflow,
    payload: WorkflowUpdate,
    repository: AgentWorkflowRepository,
    user: User,
) -> AgentWorkflow:
    previous_values = workflow_snapshot(workflow)
    changes = payload.model_dump(exclude_unset=True)
    if "steps" in changes:
        changes["steps"] = [step.model_dump() for step in payload.steps or []]
    for field, value in changes.items():
        setattr(workflow, field, value)
    workflow = repository.save(workflow)
    domain_event_bus.publish(
        WorkflowUpdated(
            actor_id=user.id,
            owner_id=workflow.user_id,
            project_id=workflow.project_id,
            workflow_id=workflow.id,
            previous_values=previous_values,
            current_values=workflow_snapshot(workflow),
        )
    )
    return workflow


def serialize_step_details(steps: list[AgentRunResponse]) -> list[dict]:
    return [
        {
            "index": index,
            "agent_id": step.agent.id,
            "agent_name": step.agent.name,
            "task": step.agent.task.value,
            "status": "completed",
            "execution_id": str(step.execution_id) if step.execution_id else None,
            "provider": step.provider,
            "model": step.model,
            "model_selection_source": step.model_selection_source,
            "routing_reason": step.routing_reason,
            "duration_ms": step.duration_ms,
            "memory_items_used": step.memory_items_used,
            "content": step.content,
        }
        for index, step in enumerate(steps, start=1)
    ]


def execute_workflow(
    *,
    workflow: AgentWorkflow,
    instruction: str,
    project_id: UUID | None,
    session_key: str | None,
    use_memory: bool,
    user: User,
    execution_repository: WorkflowExecutionRepository,
    agent_service: AgentService,
) -> WorkflowRunResponse:
    steps = [
        AgentOrchestrationStep(agent_id=step["agent_id"], instruction=step.get("instruction"))
        for step in workflow.steps
    ]
    execution = execution_repository.create(
        WorkflowExecution(
            user_id=user.id,
            workflow_id=workflow.id,
            project_id=project_id,
            workflow_name=workflow.name,
            status="running",
            instruction=instruction,
            session_key=session_key,
            use_memory=use_memory,
            steps_total=len(steps),
            step_details=[],
        )
    )

    try:
        result = AgentOrchestrator(agent_service).run(
            initial_instruction=instruction,
            steps=steps,
            user_id=user.id,
            project_id=project_id,
            session_key=session_key,
            use_memory=use_memory,
        )
    except (KeyError, ValueError) as exc:
        execution.status = "failed"
        execution.error_message = str(exc)
        execution_repository.save(execution)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ChatProviderError as exc:
        execution.status = "failed"
        execution.error_message = "Não foi possível executar o workflow nos modelos configurados."
        execution_repository.save(execution)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=execution.error_message,
        ) from exc

    execution.status = "completed"
    execution.steps_completed = len(result.steps)
    execution.total_duration_ms = result.total_duration_ms
    execution.final_content = result.final_content
    execution.step_details = serialize_step_details(result.steps)
    execution_repository.save(execution)

    return WorkflowRunResponse(
        execution_id=execution.id,
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        steps=result.steps,
        final_content=result.final_content,
        total_duration_ms=result.total_duration_ms,
        project_id=project_id,
        session_key=session_key,
        use_memory=use_memory,
    )


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(
    project_id: UUID | None = None,
    include_inactive: bool = Query(default=False),
    repository: AgentWorkflowRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[WorkflowResponse]:
    return repository.list(user_id=user.id, project_id=project_id, active_only=not include_inactive)


@router.get("/executions", response_model=list[WorkflowExecutionResponse])
def list_workflow_executions(
    workflow_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    repository: WorkflowExecutionRepository = Depends(get_execution_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[WorkflowExecutionResponse]:
    return repository.list(user_id=user.id, workflow_id=workflow_id, limit=limit)


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
def get_workflow_execution(
    execution_id: UUID,
    repository: WorkflowExecutionRepository = Depends(get_execution_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowExecutionResponse:
    execution = repository.get(execution_id=execution_id, user_id=user.id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
    return execution


@router.post("/executions/{execution_id}/retry", response_model=WorkflowRunResponse)
def retry_workflow_execution(
    execution_id: UUID,
    payload: WorkflowRunRequest,
    repository: AgentWorkflowRepository = Depends(get_repository),
    execution_repository: WorkflowExecutionRepository = Depends(get_execution_repository),
    agent_service: AgentService = Depends(get_agent_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowRunResponse:
    previous = execution_repository.get(execution_id=execution_id, user_id=user.id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
    if previous.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uma execução em andamento não pode ser repetida.",
        )

    workflow = repository.get(workflow_id=previous.workflow_id, user_id=user.id)
    if workflow is None or not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")

    instruction = (payload.instruction or previous.instruction).strip()
    return execute_workflow(
        workflow=workflow,
        instruction=instruction,
        project_id=payload.project_id if payload.project_id is not None else previous.project_id,
        session_key=payload.session_key if payload.session_key is not None else previous.session_key,
        use_memory=payload.use_memory if payload.use_memory is not None else previous.use_memory,
        user=user,
        execution_repository=execution_repository,
        agent_service=agent_service,
    )


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
    workflow = repository.create(workflow)
    domain_event_bus.publish(
        WorkflowCreated(
            actor_id=user.id,
            owner_id=workflow.user_id,
            project_id=workflow.project_id,
            workflow_id=workflow.id,
            current_values=workflow_snapshot(workflow),
        )
    )
    return workflow


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
def run_workflow(
    workflow_id: UUID,
    payload: WorkflowRunRequest,
    repository: AgentWorkflowRepository = Depends(get_repository),
    execution_repository: WorkflowExecutionRepository = Depends(get_execution_repository),
    agent_service: AgentService = Depends(get_agent_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> WorkflowRunResponse:
    workflow = repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None or not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")

    instruction = (payload.instruction or workflow.default_instruction or "").strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe uma instrução ou configure uma instrução padrão no workflow.",
        )

    return execute_workflow(
        workflow=workflow,
        instruction=instruction,
        project_id=payload.project_id if payload.project_id is not None else workflow.project_id,
        session_key=payload.session_key if payload.session_key is not None else workflow.session_key,
        use_memory=payload.use_memory if payload.use_memory is not None else workflow.use_memory,
        user=user,
        execution_repository=execution_repository,
        agent_service=agent_service,
    )


@router.post("/{workflow_id}/versions/{version_number}/restore", response_model=WorkflowResponse)
def restore_workflow_version(
    workflow_id: UUID,
    version_number: int,
    repository: AgentWorkflowRepository = Depends(get_repository),
    version_repository: ResourceVersionRepository = Depends(get_version_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> WorkflowResponse:
    workflow = repository.get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")
    version = version_repository.get(
        owner_id=workflow.user_id,
        resource_type="workflow",
        resource_id=workflow_id,
        version_number=version_number,
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow version not found.")
    allowed_fields = {
        "name",
        "description",
        "project_id",
        "steps",
        "default_instruction",
        "session_key",
        "use_memory",
        "is_active",
    }
    payload = WorkflowUpdate(**{key: value for key, value in version.snapshot.items() if key in allowed_fields})
    return apply_workflow_update(workflow=workflow, payload=payload, repository=repository, user=user)


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
    return apply_workflow_update(workflow=workflow, payload=payload, repository=repository, user=user)


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
    workflow = repository.save(workflow)
    domain_event_bus.publish(
        WorkflowArchived(
            actor_id=user.id,
            owner_id=workflow.user_id,
            project_id=workflow.project_id,
            workflow_id=workflow.id,
            current_values=workflow_snapshot(workflow),
        )
    )
    return workflow
