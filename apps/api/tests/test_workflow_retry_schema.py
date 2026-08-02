from app.schemas.workflows import WorkflowRunRequest


def test_workflow_retry_can_reuse_original_execution_values() -> None:
    payload = WorkflowRunRequest()

    assert payload.instruction is None
    assert payload.project_id is None
    assert payload.session_key is None
    assert payload.use_memory is None
