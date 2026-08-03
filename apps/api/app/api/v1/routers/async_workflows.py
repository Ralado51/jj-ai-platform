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
from app.schemas.agents import AgentRunResponse
from app.schemas.workflows import (
    WorkflowExecutionResponse,
    WorkflowRetryFromStepRequest,
    WorkflowRunRequest,
)
from app.services.agent_orchestrator import (
    AgentOrchestrationCancelled,
    AgentOrchestrationStep,
    AgentOrchestrator,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _serialize_step_details(steps: list[AgentRunResponse], *, offset: int = 0) -> list[dict]:
    details = serialize_step_details(steps)
    for detail in details:
        detail["index"] += offset
    return details


def _run_workflow_in_background(
    *,
    execution_id: UUID,
    user_id: UUID,
    start_step: int = 1,
    initial_input: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        execution_repository = WorkflowExecutionRepository(db)
        execution = execution_repository.get(execution_id=execution_id, user_id=user_id)
        if execution is None or execution.status == "cancelled":
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
            for step in workflow.steps[start_step - 1 :]
        ]
        completed_steps: list[AgentRunResponse] = []
        prefix_details = list(execution.step_details or [])[: start_step - 1]

        def should_cancel() -> bool:
            db.expire_all()
            current = execution_repository.get(execution_id=execution_id, user_id=user_id)
            return current is None or current.status in {"cancelling", "cancelled"}

        def on_step_completed(_: int, result: AgentRunResponse) -> None:
            completed_steps.append(result)
            db.expire_all()
            current = execution_repository.get(execution_id=execution_id, user_id=user_id)
            if current is None:
                return
            current.steps_completed = (start_step - 1) + len(completed_steps)
            current.total_duration_ms = sum(
                int(item.get("duration_ms", 0)) for item in prefix_details
            ) + sum(item.duration_ms for item in completed_steps)
            current.step_details = prefix_details + _serialize_step_details(
                completed_steps,
                offset=start_step - 1,
            )
            current.final_content = completed_steps[-1].content
            execution_repository.save(current)

        try:
            result = AgentOrchestrator(get_agent_service(db)).run(
                initial_instruction=initial_input or execution.instruction,
                steps=steps,
                user_id=user_id,
                project_id=execution.project_id,
                session_key=execution.session_key,
                use_memory=execution.use_memory,
                should_cancel=should_cancel,
                on_step_completed=on_step_completed,
            )
        except AgentOrchestrationCancelled as exc:
            db.expire_all()
            current = execution_repository.get(execution_id=execution_id, user_id=user_id)
            if current is not None:
                current.status = "cancelled"
                current.steps_completed = (start_step - 1) + len(exc.completed_steps)
                current.total_duration_ms = sum(
                    int(item.get("duration_ms", 0)) for item in prefix_details
                ) + sum(item.duration_ms for item in exc.completed_steps)
                current.step_details = prefix_details + _serialize_step_details(
                    exc.completed_steps,
                    offset=start_step - 1,
                )
                current.final_content = (
                    exc.completed_steps[-1].content
                    if exc.completed_steps
                    else (prefix_details[-1].get("content") if prefix_details else None)
                )
                current.error_message = None
                execution_repository.save(current)
            return

        db.expire_all()
        execution = execution_repository.get(execution_id=execution_id, user_id=user_id)
        if execution is None:
            return
        execution.status = "completed"
        execution.steps_completed = len(workflow.steps)
        execution.total_duration_ms = sum(
            int(item.get("duration_ms", 0)) for item in prefix_details
        ) + result.total_duration_ms
        execution.final_content = result.final_content
        execution.step_details = prefix_details + _serialize_step_details(
            result.steps,
            offset=start_step - 1,
        )
        execution.error_message = None
        execution_repository.save(execution)
    except Exception as exc:  # noqa: BLE001 - background jobs must always persist their terminal state
        db.rollback()
        execution = WorkflowExecutionRepository(db).get(
            execution_id=execution_id,
            user_id=user_id,
        )
        if execution is not None and execution.status not in {"cancelling", "cancelled"}:
            execution.status = "failed"
            execution.error_message = str(exc)[:2000]
            WorkflowExecutionRepository(db).save(execution)
    finally:
        db.close()


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=WorkflowExecutionResponse,
)
def cancel_workflow_execution(
    execution_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> WorkflowExecutionResponse:
    repository = WorkflowExecutionRepository(db)
    execution = repository.get(execution_id=execution_id, user_id=user.id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
    if execution.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A execução já foi finalizada e não pode ser cancelada.",
        )

    execution.status = "cancelled" if execution.status == "pending" else "cancelling"
    execution.error_message = None
    return WorkflowExecutionResponse.model_validate(repository.save(execution))


@router.post(
    "/executions/{execution_id}/retry-from-step",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_workflow_execution_from_step(
    execution_id: UUID,
    payload: WorkflowRetryFromStepRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> WorkflowExecutionResponse:
    execution_repository = WorkflowExecutionRepository(db)
    previous = execution_repository.get(execution_id=execution_id, user_id=user.id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")
    if previous.status in {"pending", "running", "cancelling"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aguarde a execução atual terminar antes de repetir uma etapa.",
        )

    workflow = AgentWorkflowRepository(db).get(
        workflow_id=previous.workflow_id,
        user_id=user.id,
    )
    if workflow is None or not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow não encontrado.")
    if payload.step > len(workflow.steps):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A etapa informada não existe neste workflow.",
        )

    prefix_details = list(previous.step_details or [])[: payload.step - 1]
    if payload.step > 1 and len(prefix_details) < payload.step - 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não há saída anterior suficiente para reiniciar nesta etapa.",
        )

    initial_input = (
        str(prefix_details[-1].get("content", "")).strip()
        if payload.step > 1
        else (payload.instruction or previous.instruction).strip()
    )
    if not initial_input:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível determinar a entrada para a etapa selecionada.",
        )

    project_id = payload.project_id if payload.project_id is not None else previous.project_id
    session_key = payload.session_key if payload.session_key is not None else previous.session_key
    use_memory = payload.use_memory if payload.use_memory is not None else previous.use_memory

    execution = execution_repository.create(
        WorkflowExecution(
            user_id=user.id,
            workflow_id=workflow.id,
            project_id=project_id,
            parent_execution_id=previous.id,
            retry_from_step=payload.step,
            workflow_name=workflow.name,
            status="pending",
            instruction=payload.instruction or previous.instruction,
            session_key=session_key,
            use_memory=use_memory,
            steps_total=len(workflow.steps),
            steps_completed=payload.step - 1,
            total_duration_ms=sum(
                int(item.get("duration_ms", 0)) for item in prefix_details
            ),
            final_content=(
                prefix_details[-1].get("content") if prefix_details else None
            ),
            step_details=prefix_details,
        )
    )
    background_tasks.add_task(
        _run_workflow_in_background,
        execution_id=execution.id,
        user_id=user.id,
        start_step=payload.step,
        initial_input=initial_input,
    )
    return WorkflowExecutionResponse.model_validate(execution)


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
