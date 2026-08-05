from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.events.bus import DomainEventBus, domain_event_bus
from app.events.types import PromptEvaluationFinished
from app.models.prompt_evaluation import PromptEvaluation
from app.models.prompt_template import PromptTemplate
from app.models.user import User, UserRole
from app.repositories.prompt_evaluation_repository import PromptEvaluationRepository
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.schemas.prompt_evaluations import PromptEvaluationCreate
from app.services.chat_providers import ChatProvider, OllamaChatProvider


class PromptEvaluationService:
    def __init__(
        self,
        repository: PromptEvaluationRepository,
        version_repository: ResourceVersionRepository,
        *,
        provider: ChatProvider | None = None,
        event_bus: DomainEventBus = domain_event_bus,
    ) -> None:
        self.repository = repository
        self.version_repository = version_repository
        self.provider = provider or self._build_provider()
        self.event_bus = event_bus

    def run(self, *, template: PromptTemplate, payload: PromptEvaluationCreate, user: User) -> PromptEvaluation:
        if template.owner_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para avaliar este template.")
        owner_id = template.owner_id or user.id
        snapshot = self._snapshot(template)
        if payload.prompt_version is not None:
            version = self.version_repository.get(
                owner_id=owner_id,
                resource_type="prompt",
                resource_id=template.id,
                version_number=payload.prompt_version,
            )
            if version is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found.")
            snapshot = version.snapshot

        started_at = perf_counter()
        results: list[dict] = []
        try:
            for case in payload.cases:
                case_started_at = perf_counter()
                system_prompt = self._render(snapshot["content"], case.variables)
                output = self.provider.generate(system_prompt=system_prompt, user_prompt=case.input)
                score, matched, missing = self._score(
                    output=output,
                    expected_output=case.expected_output,
                    expected_keywords=case.expected_keywords,
                )
                results.append(
                    {
                        "name": case.name,
                        "output": output,
                        "score": score,
                        "passed": score >= 0.8,
                        "matched_keywords": matched,
                        "missing_keywords": missing,
                        "duration_ms": max(0, round((perf_counter() - case_started_at) * 1000)),
                    }
                )
            evaluation_status = "completed"
            error = None
        except Exception as exc:
            evaluation_status = "failed"
            error = str(exc)[:2000]
        duration_ms = max(0, round((perf_counter() - started_at) * 1000))
        average_score = round(sum(item["score"] for item in results) / len(payload.cases), 4)
        evaluation = self.repository.create(
            values={
                "owner_id": owner_id,
                "project_id": template.project_id,
                "prompt_id": template.id,
                "prompt_version": payload.prompt_version,
                "name": payload.name,
                "status": evaluation_status,
                "provider": self.provider.name,
                "model": self.provider.model,
                "dataset": [case.model_dump() for case in payload.cases],
                "results": results,
                "score": average_score,
                "duration_ms": duration_ms,
                "error": error,
            }
        )
        self.event_bus.publish(
            PromptEvaluationFinished(
                actor_id=user.id,
                project_id=template.project_id,
                evaluation_id=evaluation.id,
                prompt_id=template.id,
                prompt_version=payload.prompt_version,
                status=evaluation_status,
                score=average_score,
                provider=self.provider.name,
                model=self.provider.model,
            )
        )
        return evaluation

    def list(self, *, template: PromptTemplate, user: User, offset: int, limit: int) -> tuple[list[PromptEvaluation], int]:
        owner_id = template.owner_id or user.id
        return self.repository.list(owner_id=owner_id, prompt_id=template.id, offset=offset, limit=limit)

    @staticmethod
    def _render(content: str, variables: dict[str, str]) -> str:
        rendered = content
        for name, value in variables.items():
            rendered = rendered.replace("{{" + name + "}}", value)
        return rendered

    @staticmethod
    def _score(*, output: str, expected_output: str | None, expected_keywords: list[str]) -> tuple[float, list[str], list[str]]:
        normalized = " ".join(output.casefold().split())
        keywords = [keyword.strip() for keyword in expected_keywords if keyword.strip()]
        matched = [keyword for keyword in keywords if keyword.casefold() in normalized]
        missing = [keyword for keyword in keywords if keyword not in matched]
        keyword_score = len(matched) / len(keywords) if keywords else None
        exact_score = float(" ".join((expected_output or "").casefold().split()) == normalized) if expected_output else None
        scores = [score for score in (keyword_score, exact_score) if score is not None]
        return (round(sum(scores) / len(scores), 4), matched, missing)

    @staticmethod
    def _snapshot(template: PromptTemplate) -> dict:
        return {"content": template.content}

    @staticmethod
    def _build_provider() -> OllamaChatProvider:
        settings = get_settings()
        return OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
            timeout_seconds=settings.ollama_chat_timeout_seconds,
            temperature=settings.ollama_chat_temperature,
            max_tokens=settings.ollama_chat_max_tokens,
            repeat_penalty=settings.ollama_chat_repeat_penalty,
            max_characters=settings.ollama_chat_max_characters,
        )
