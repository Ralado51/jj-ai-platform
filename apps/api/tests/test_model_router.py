import pytest

from app.services.model_router import AITaskType, ModelRouter


def test_routes_content_generation_to_configured_model() -> None:
    router = ModelRouter(
        default_model="qwen2.5:3b",
        content_model="gemma3:4b",
    )

    route = router.route(AITaskType.CONTENT_GENERATION)

    assert route.task == AITaskType.CONTENT_GENERATION
    assert route.model == "gemma3:4b"
    assert route.used_fallback is False
    assert "content_generation" in route.reason


def test_uses_default_model_when_task_model_is_not_configured() -> None:
    router = ModelRouter(default_model="qwen2.5:3b", coding_model="")

    route = router.route(AITaskType.CODING)

    assert route.model == "qwen2.5:3b"
    assert route.used_fallback is True
    assert "modelo padrão" in route.reason


def test_rejects_empty_default_model() -> None:
    with pytest.raises(ValueError, match="default_model"):
        ModelRouter(default_model="   ")
