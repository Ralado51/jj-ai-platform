from uuid import uuid4

from app.schemas.workflows import WorkflowExecutionResponse


def test_workflow_execution_response_exposes_retry_lineage() -> None:
    parent_id = uuid4()
    payload = {
        "id": uuid4(),
        "workflow_id": uuid4(),
        "project_id": None,
        "parent_execution_id": parent_id,
        "retry_from_step": 3,
        "workflow_name": "Pipeline de conteúdo",
        "status": "pending",
        "instruction": "Crie o conteúdo.",
        "session_key": None,
        "use_memory": True,
        "steps_total": 4,
        "steps_completed": 2,
        "total_duration_ms": 1000,
        "final_content": "resultado parcial",
        "error_message": None,
        "step_details": [],
        "created_at": "2026-08-03T12:00:00Z",
        "updated_at": "2026-08-03T12:00:00Z",
    }

    response = WorkflowExecutionResponse.model_validate(payload)

    assert response.parent_execution_id == parent_id
    assert response.retry_from_step == 3


def test_workflow_execution_response_keeps_legacy_rows_compatible() -> None:
    payload = {
        "id": uuid4(),
        "workflow_id": uuid4(),
        "project_id": None,
        "workflow_name": "Pipeline legado",
        "status": "completed",
        "instruction": "Execute.",
        "session_key": None,
        "use_memory": False,
        "steps_total": 1,
        "steps_completed": 1,
        "total_duration_ms": 100,
        "final_content": "ok",
        "error_message": None,
        "step_details": [],
        "created_at": "2026-08-03T12:00:00Z",
        "updated_at": "2026-08-03T12:00:00Z",
    }

    response = WorkflowExecutionResponse.model_validate(payload)

    assert response.parent_execution_id is None
    assert response.retry_from_step is None
