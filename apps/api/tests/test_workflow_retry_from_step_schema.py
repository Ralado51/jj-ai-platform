import pytest
from pydantic import ValidationError

from app.schemas.workflows import WorkflowRetryFromStepRequest


def test_retry_from_step_accepts_valid_step() -> None:
    payload = WorkflowRetryFromStepRequest(step=3, use_memory=False)

    assert payload.step == 3
    assert payload.use_memory is False


def test_retry_from_step_rejects_step_outside_workflow_limit() -> None:
    with pytest.raises(ValidationError):
        WorkflowRetryFromStepRequest(step=0)

    with pytest.raises(ValidationError):
        WorkflowRetryFromStepRequest(step=7)
