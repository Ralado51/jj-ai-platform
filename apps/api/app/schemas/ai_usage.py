from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AIUsageSummaryResponse(BaseModel):
    total_requests: int
    total_tokens: int
    estimated_cost: Decimal
    cache_hits: int
    ollama_savings: Decimal
    average_latency_ms: float


class AIUsageRecordRequest(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    project_id: UUID | None = None
    workflow_execution_id: UUID | None = None
    workflow_step: int | None = None
    agent_id: UUID | None = None
    task: str | None = None
    cached_response: bool = False
    request_started_at: dt.datetime
    request_finished_at: dt.datetime
