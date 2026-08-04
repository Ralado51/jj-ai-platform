from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.models.ai_usage import AIUsage
from app.repositories.ai_usage_repository import AIUsageRepository

MODEL_PRICING_PER_MILLION: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-5": (Decimal("1.25"), Decimal("10.00")),
    "gpt-4.1": (Decimal("2.00"), Decimal("8.00")),
    "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
}
DEFAULT_EQUIVALENT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class UsageMeasurement:
    user_id: UUID
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    started_at: dt.datetime
    finished_at: dt.datetime
    project_id: UUID | None = None
    workflow_execution_id: UUID | None = None
    workflow_step: int | None = None
    agent_id: UUID | None = None
    task: str | None = None
    cached_response: bool = False


class AIUsageService:
    def __init__(self, repository: AIUsageRepository) -> None:
        self.repository = repository

    @staticmethod
    def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> tuple[Decimal, Decimal, Decimal]:
        input_rate, output_rate = MODEL_PRICING_PER_MILLION.get(model, (Decimal("0"), Decimal("0")))
        input_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * input_rate
        output_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * output_rate
        return input_cost, output_cost, input_cost + output_cost

    def record(self, measurement: UsageMeasurement) -> AIUsage:
        prompt_tokens = max(0, measurement.prompt_tokens)
        completion_tokens = max(0, measurement.completion_tokens)
        input_cost, output_cost, total_cost = self.estimate_cost(measurement.model, prompt_tokens, completion_tokens)
        equivalent_cost = total_cost
        if measurement.provider.lower() == "ollama":
            _, _, equivalent_cost = self.estimate_cost(DEFAULT_EQUIVALENT_MODEL, prompt_tokens, completion_tokens)
            input_cost = output_cost = total_cost = Decimal("0")
        return self.repository.create(
            measurement=measurement,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            equivalent_openai_cost=equivalent_cost,
        )
