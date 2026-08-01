from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.benchmark import (
    BenchmarkModelResultResponse,
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    BenchmarkScoresResponse,
)
from app.services.chat_providers import ChatProviderError, OllamaChatProvider
from app.services.prompt_evaluator import PromptEvaluator


@dataclass(frozen=True)
class _BenchmarkOutcome:
    model: str
    duration_ms: int
    response: str
    estimated_tokens: int
    success: bool
    error: str | None
    scores: BenchmarkScoresResponse | None


class BenchmarkService:
    def __init__(self, repository: BenchmarkRepository | None = None) -> None:
        self.settings = get_settings()
        self.evaluator = PromptEvaluator()
        self.repository = repository

    def run(
        self,
        payload: BenchmarkRunRequest,
        *,
        user_id: UUID | None = None,
    ) -> BenchmarkRunResponse:
        models = self._normalize_models(payload.models)
        outcomes = [self._run_model(model=model, payload=payload) for model in models]
        successful = [item for item in outcomes if item.success and item.scores is not None]
        winner = None
        if successful:
            winner = max(
                successful,
                key=lambda item: (
                    item.scores.overall if item.scores is not None else 0,
                    -item.duration_ms,
                ),
            ).model

        result = BenchmarkRunResponse(
            winner=winner,
            results=[
                BenchmarkModelResultResponse(
                    model=item.model,
                    duration_ms=item.duration_ms,
                    response=item.response,
                    estimated_tokens=item.estimated_tokens,
                    success=item.success,
                    error=item.error,
                    scores=item.scores,
                )
                for item in sorted(
                    outcomes,
                    key=lambda item: (
                        -(item.scores.overall if item.scores is not None else -1),
                        item.duration_ms,
                    ),
                )
            ],
        )
        if self.repository is not None and user_id is not None:
            self.repository.save(user_id=user_id, payload=payload, result=result)
        return result

    def _run_model(self, *, model: str, payload: BenchmarkRunRequest) -> _BenchmarkOutcome:
        provider = OllamaChatProvider(
            base_url=self.settings.ollama_base_url,
            model=model,
            timeout_seconds=self.settings.ollama_chat_timeout_seconds,
            temperature=self.settings.ollama_chat_temperature,
        )
        started_at = perf_counter()
        try:
            response = provider.generate(
                system_prompt=payload.system_prompt,
                user_prompt=payload.prompt,
            )
            duration_ms = max(0, round((perf_counter() - started_at) * 1000))
            evaluation = self.evaluator.evaluate(response)
            scores = evaluation.scores
            return _BenchmarkOutcome(
                model=model,
                duration_ms=duration_ms,
                response=response,
                estimated_tokens=self._estimate_tokens(payload.system_prompt, payload.prompt, response),
                success=True,
                error=None,
                scores=BenchmarkScoresResponse(
                    hook=scores.hook,
                    storytelling=scores.storytelling,
                    clarity=scores.clarity,
                    originality=scores.originality,
                    call_to_action=scores.call_to_action,
                    structure=scores.structure,
                    overall=scores.overall,
                ),
            )
        except (httpx.HTTPError, ChatProviderError) as exc:
            duration_ms = max(0, round((perf_counter() - started_at) * 1000))
            return _BenchmarkOutcome(
                model=model,
                duration_ms=duration_ms,
                response="",
                estimated_tokens=self._estimate_tokens(payload.system_prompt, payload.prompt),
                success=False,
                error=str(exc),
                scores=None,
            )

    @staticmethod
    def _normalize_models(models: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(model.strip() for model in models if model.strip()))
        if len(normalized) < 2:
            raise ValueError("At least two distinct models are required")
        return normalized

    @staticmethod
    def _estimate_tokens(*parts: str) -> int:
        characters = sum(len(part) for part in parts)
        return max(1, round(characters / 4))
