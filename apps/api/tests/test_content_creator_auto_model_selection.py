from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.services.content_creator_service import ContentCreatorService
from app.services.model_router import AITaskType, ModelRouter


@dataclass
class _CandidateRepository:
    candidate: dict | None

    def best_model(
        self,
        *,
        user_id,
        task: AITaskType,
        minimum_samples: int,
        minimum_average_score: float,
    ):
        del user_id, minimum_samples, minimum_average_score
        assert task is AITaskType.CONTENT_GENERATION
        return self.candidate


def test_content_creator_uses_benchmark_winner(monkeypatch):
    monkeypatch.setattr(
        "app.services.content_creator_service.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "ollama_chat_model": "qwen2.5:3b",
                "ollama_content_model": "gemma3:4b",
                "ollama_rag_model": "",
                "ollama_coding_model": "",
                "ollama_summarization_model": "",
                "ollama_general_model": "",
                "ollama_base_url": "http://ollama:11434",
                "ollama_chat_timeout_seconds": 180.0,
                "ollama_chat_temperature": 0.2,
                "auto_model_selection_enabled": True,
                "auto_model_minimum_samples": 3,
                "auto_model_minimum_average_score": 7.0,
            },
        )(),
    )

    service = ContentCreatorService(
        benchmark_repository=_CandidateRepository(
            {
                "model": "llama3.1:8b",
                "executions": 5,
                "average_score": 9.1,
                "average_duration_ms": 4200,
            }
        ),
        user_id=uuid4(),
    )

    assert service.route.task is AITaskType.CONTENT_GENERATION
    assert service.route.model == "llama3.1:8b"
    assert service.provider.model == "llama3.1:8b"
    assert "histórico de benchmarks" in service.route.reason.lower()


def test_content_creator_falls_back_to_configured_router(monkeypatch):
    monkeypatch.setattr(
        "app.services.content_creator_service.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "ollama_chat_model": "qwen2.5:3b",
                "ollama_content_model": "gemma3:4b",
                "ollama_rag_model": "",
                "ollama_coding_model": "",
                "ollama_summarization_model": "",
                "ollama_general_model": "",
                "ollama_base_url": "http://ollama:11434",
                "ollama_chat_timeout_seconds": 180.0,
                "ollama_chat_temperature": 0.2,
                "auto_model_selection_enabled": True,
                "auto_model_minimum_samples": 3,
                "auto_model_minimum_average_score": 7.0,
            },
        )(),
    )

    router = ModelRouter(
        default_model="qwen2.5:3b",
        content_model="gemma3:4b",
    )
    service = ContentCreatorService(
        model_router=router,
        benchmark_repository=_CandidateRepository(None),
        user_id=uuid4(),
    )

    assert service.route.model == "gemma3:4b"
    assert service.provider.model == "gemma3:4b"
    assert service.route.used_fallback is False
