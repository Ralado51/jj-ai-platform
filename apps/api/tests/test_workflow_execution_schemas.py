from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.workflows import WorkflowExecutionResponse, WorkflowRunResponse


def test_workflow_execution_response_accepts_completed_run() -> None:
    now = datetime.now(UTC)
    payload = WorkflowExecutionResponse(
        id=uuid4(),
        workflow_id=uuid4(),
        project_id=None,
        workflow_name="Pipeline de conteúdo",
        status="completed",
        instruction="Crie um roteiro.",
        session_key="campanha-agosto",
        use_memory=True,
        steps_total=3,
        steps_completed=3,
        total_duration_ms=4200,
        final_content="Roteiro final",
        error_message=None,
        created_at=now,
        updated_at=now,
    )

    assert payload.status == "completed"
    assert payload.steps_completed == payload.steps_total


def test_workflow_run_response_requires_execution_id() -> None:
    execution_id = uuid4()
    payload = WorkflowRunResponse(
        execution_id=execution_id,
        workflow_id=uuid4(),
        workflow_name="Pipeline",
        steps=[],
        final_content="Resultado",
        total_duration_ms=100,
        use_memory=False,
    )

    assert payload.execution_id == execution_id
