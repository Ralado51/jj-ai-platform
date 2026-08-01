from uuid import uuid4

from app.services.auto_model_selector import AutoModelSelector
from app.services.model_router import AITaskType, ModelRouter


class FakeBenchmarkRepository:
    def __init__(self, candidate=None):
        self.candidate = candidate
        self.calls = []

    def best_model(self, **kwargs):
        self.calls.append(kwargs)
        return self.candidate


def build_router() -> ModelRouter:
    return ModelRouter(
        default_model="qwen2.5:3b",
        content_model="gemma3:4b",
        rag_model="qwen2.5:3b",
    )


def test_selects_best_model_from_benchmark_history():
    repository = FakeBenchmarkRepository(
        {
            "model": "llama3.1:8b",
            "executions": 5,
            "average_score": 9.1,
            "average_duration_ms": 3200,
        }
    )
    selector = AutoModelSelector(repository=repository, router=build_router())

    result = selector.select(user_id=uuid4(), task=AITaskType.CONTENT_GENERATION)

    assert result.model == "llama3.1:8b"
    assert result.source == "benchmark_history"
    assert result.sample_size == 5
    assert result.used_fallback is False


def test_falls_back_to_configured_router_when_history_is_insufficient():
    repository = FakeBenchmarkRepository(None)
    selector = AutoModelSelector(repository=repository, router=build_router())

    result = selector.select(user_id=uuid4(), task=AITaskType.CONTENT_GENERATION)

    assert result.model == "gemma3:4b"
    assert result.source == "configured_router"
    assert result.sample_size == 0
    assert result.used_fallback is False


def test_validates_selection_thresholds():
    repository = FakeBenchmarkRepository(None)

    try:
        AutoModelSelector(
            repository=repository,
            router=build_router(),
            minimum_samples=0,
        )
    except ValueError as exc:
        assert "minimum_samples" in str(exc)
    else:
        raise AssertionError("Expected minimum_samples validation error")
