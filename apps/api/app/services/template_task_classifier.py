from __future__ import annotations

from dataclasses import dataclass

from app.services.model_router import AITaskType


@dataclass(frozen=True)
class TemplateTaskClassification:
    task: AITaskType
    reason: str


class TemplateTaskClassifier:
    """Classifies prompt templates without requiring a database migration."""

    KEYWORDS = {
        AITaskType.CODING: (
            "código",
            "codigo",
            "python",
            "javascript",
            "typescript",
            "sql",
            "debug",
            "refator",
            "api",
        ),
        AITaskType.SUMMARIZATION: (
            "resum",
            "sintetiz",
            "analisar um novo conteúdo",
            "analisar conteudo",
            "principais pontos",
        ),
        AITaskType.CONTENT_GENERATION: (
            "criar conteúdo",
            "criador de conteúdo",
            "post",
            "roteiro",
            "legenda",
            "copy",
            "linkedin",
            "instagram",
            "tiktok",
        ),
        AITaskType.RAG: (
            "documento",
            "fonte",
            "base de conhecimento",
            "contexto fornecido",
        ),
    }

    def classify(self, *, name: str, description: str = "", prompt: str = "") -> TemplateTaskClassification:
        normalized = " ".join(f"{name} {description} {prompt}".lower().split())

        for task in (
            AITaskType.CODING,
            AITaskType.SUMMARIZATION,
            AITaskType.CONTENT_GENERATION,
            AITaskType.RAG,
        ):
            matched = next((keyword for keyword in self.KEYWORDS[task] if keyword in normalized), None)
            if matched:
                return TemplateTaskClassification(
                    task=task,
                    reason=f"Template classificado como {task.value} pela palavra-chave '{matched}'.",
                )

        return TemplateTaskClassification(
            task=AITaskType.GENERAL,
            reason="Nenhuma regra específica foi encontrada; usando tarefa general.",
        )
