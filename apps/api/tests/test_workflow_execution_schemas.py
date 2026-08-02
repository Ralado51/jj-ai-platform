from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.workflows import WorkflowExecutionResponse, WorkflowRunResponse


def test_workflow_execution_response_accepts_completed_run() -> None:
    now = datetime.now(UTC)
    agent_execution_id = uuid4()
    payload = WorkflowExecutionResponse(
        id=uuid4(),
        workflow_id=uuid4(),
        project_id=None,
        workflow_name="Pipeline de conteúdo",
        status="completed",
        instruction="Crie um roteiro.",
        session_key="campanha-agosto",
        use_memory=True,
        steps_total=1,
        steps_completed=1,
        total_duration_ms=4200,
        final_content="Roteiro final",
        error_message=None,
        step_details=[
            {
                "index": 1,
                "agent_id": "content-creator",
                "agent_name": "Criador de Conteúdo",
                "task": "content_generation",
                "status": "completed",
                "execution_id": agent_execution_id,
                "provider": "ollama",
                "model": "qwen2.5:3b",
                "model_selection_source": "benchmark_history",
                "routing_reason": "Modelo selecionado pelo histórico de benchmarks.",
                "duration_ms": 4200,
                "memory_items_used": 2,
                "content": "Roteiro final",
            }
        ],
        created_at=now,
        updated_at=now,
    )

    assert payload.status == "completed"
    assert payload.steps_completed == payload.steps_total
    assert payload.step_details[0].execution_id == agent_execution_id
    assert payload.step_details[0].model == "qwen2.5:3b"


def test_workflow_execution_response_defaults_to_empty_step_details() -> None:
    now = datetime.now(UTC)
    payload = WorkflowExecutionResponse(
        id=uuid4(),
        workflow_id=uuid4(),
        project_id=None,
        workflow_name="Pipeline antigo",
        status="completed",
        instruction="Execute.",
        session_key=None,
        use_memory=False,
        steps_total=1,
        steps_completed=1,
        total_duration_ms=100,
        final_content="Resultado",
        error_message=None,
        created_at=now,
        updated_at=now,
    )

    assert payload.step_details == []


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
