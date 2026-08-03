from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.api.v1.routers.agents import get_service as get_agent_service
from app.api.v1.routers.workflows import serialize_step_details
from app.db.dependencies import get_db
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.workflow_execution import WorkflowExecution
from app.repositories.agent_workflow_repository import AgentWorkflowRepository
from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.schemas.workflows import WorkflowExecutionResponse, WorkflowRunRequest
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _run_workflow_in_background(*, execution_id: UUID, user_id: UUID) -> None:
    db = SessionLocal()
    try:
        execution_repository = WorkflowExecutionRepository(db)
        execution = execution_repository.get(execution_id=execution_id, user_id=user_id)
        if execution is None:
            return

        workflow = AgentWorkflowRepository(db).get(
            workflow_id=execution.workflow_id,
            user_id=user_id,
        )
        if workflow is None or not workflow.is_active:
            execution.status = "failed"
            execution.error_message = "Workflow não encontrado ou arquivado."
            execution_repository.save(execution)
            return

        execution.status = "running"
        execution_repository.save(execution)

        steps = [
            AgentOrchestrationStep(
                agent_id=step["agent_id"],
                instruction=step.get("instruction"),
            )
            for step in workflow.steps
        ]
        result = AgentOrchestrator(get_agent_service(db)).run(
            initial_instruction=execution.instruction,
            steps=steps,
            user_id=user_id,
            project_id=execution.project_id,
            session_key=execution.session_key,
            use_memory=execution.use_memory,
        )

        execution.status = "completed"
        execution.steps_completed = len(result.steps)
        execution.total_duration_ms = result.total_duration_ms
        execution.final_content = result.final_content
        execution.step_details = serialize_step_details(result.steps)
        execution.error_message = None
        execution_repository.save(execution)
    except Exception as exc:  # noqa: BLE001 - background jobs must always persist their terminal state
        db.rollback()
        execution = WorkflowExecutionRepository(db).get(
            execution_id=execution_id,
            user_id=user_id,
        )
        if execution is not None:
            execution.status = "failed"
            execution.error_message = str(exc)[:2000]
            WorkflowExecutionRepository(db).save(execution)
    finally:
        db.close()


@router.post(
    "/{workflow_id}/run/async",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_workflow_async(
    workflow_id: UUID,
    payload: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> WorkflowExecutionResponse:
    workflow = AgentWorkflowRepository(db).get(workflow_id=workflow_id, user_id=user.id)
    if workflow is None or not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")

    instruction = (payload.instruction or workflow.default_instruction or "").strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe uma instrução ou configure uma instrução padrão no workflow.",
        )

    project_id = payload.project_id if payload.project_id is not None else workflow.project_id
    session_key = payload.session_key if payload.session_key is not None else workflow.session_key
    use_memory = payload.use_memory if payload.use_memory is not None else workflow.use_memory

    execution = WorkflowExecutionRepository(db).create(
        WorkflowExecution(
            user_id=user.id,
            workflow_id=workflow.id,
            project_id=project_id,
            workflow_name=workflow.name,
            status="pending",
            instruction=instruction,
            session_key=session_key,
            use_memory=use_memory,
            steps_total=len(workflow.steps),
            steps_completed=0,
            step_details=[],
        )
    )
    background_tasks.add_task(
        _run_workflow_in_background,
        execution_id=execution.id,
        user_id=user.id,
    )
    return WorkflowExecutionResponse.model_validate(execution)
