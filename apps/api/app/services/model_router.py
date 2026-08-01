from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AITaskType(StrEnum):
    CONTENT_GENERATION = "content_generation"
    RAG = "rag"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    GENERAL = "general"


@dataclass(frozen=True)
class ModelRoute:
    task: AITaskType
    model: str
    reason: str
    used_fallback: bool = False


class ModelRouter:
    """Selects a configured Ollama model for a known AI task."""

    def __init__(
        self,
        *,
        default_model: str,
        content_model: str | None = None,
        rag_model: str | None = None,
        coding_model: str | None = None,
        summarization_model: str | None = None,
        general_model: str | None = None,
    ) -> None:
        if not default_model.strip():
            raise ValueError("default_model must not be empty")

        self.default_model = default_model.strip()
        self.models = {
            AITaskType.CONTENT_GENERATION: self._normalize(content_model),
            AITaskType.RAG: self._normalize(rag_model),
            AITaskType.CODING: self._normalize(coding_model),
            AITaskType.SUMMARIZATION: self._normalize(summarization_model),
            AITaskType.GENERAL: self._normalize(general_model),
        }

    def route(self, task: AITaskType) -> ModelRoute:
        configured_model = self.models.get(task)
        if configured_model:
            return ModelRoute(
                task=task,
                model=configured_model,
                reason=f"Modelo configurado para a tarefa {task.value}.",
                used_fallback=False,
            )

        return ModelRoute(
            task=task,
            model=self.default_model,
            reason=(
                f"Nenhum modelo específico foi configurado para {task.value}; "
                "usando o modelo padrão do Ollama."
            ),
            used_fallback=True,
        )

    @staticmethod
    def _normalize(model: str | None) -> str | None:
        if model is None:
            return None
        normalized = model.strip()
        return normalized or None
