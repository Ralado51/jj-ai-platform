import pytest
from pydantic import ValidationError

from app.schemas.workflows import WorkflowCreate, WorkflowRunRequest


def test_workflow_requires_at_least_one_step() -> None:
    with pytest.raises(ValidationError):
        WorkflowCreate(name="Pipeline", steps=[])


def test_workflow_accepts_up_to_six_steps() -> None:
    payload = WorkflowCreate(
        name="Pipeline de conteúdo",
        steps=[{"agent_id": "general"} for _ in range(6)],
        default_instruction="Prepare o conteúdo final.",
    )

    assert len(payload.steps) == 6
    assert payload.use_memory is True


def test_workflow_rejects_more_than_six_steps() -> None:
    with pytest.raises(ValidationError):
        WorkflowCreate(
            name="Pipeline excessivo",
            steps=[{"agent_id": "general"} for _ in range(7)],
        )


def test_workflow_run_allows_using_saved_defaults() -> None:
    payload = WorkflowRunRequest()

    assert payload.instruction is None
    assert payload.project_id is None
    assert payload.session_key is None
    assert payload.use_memory is None


def test_workflow_run_accepts_runtime_overrides() -> None:
    payload = WorkflowRunRequest(
        instruction="Execute este objetivo agora.",
        session_key="execucao-manual",
        use_memory=False,
    )

    assert payload.instruction == "Execute este objetivo agora."
    assert payload.session_key == "execucao-manual"
    assert payload.use_memory is False


def test_workflow_run_rejects_too_short_instruction() -> None:
    with pytest.raises(ValidationError):
        WorkflowRunRequest(instruction="x")
