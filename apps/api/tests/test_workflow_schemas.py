import pytest
from pydantic import ValidationError

from app.schemas.workflows import WorkflowCreate


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
