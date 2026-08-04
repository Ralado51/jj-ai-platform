from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsage

if TYPE_CHECKING:
    from app.services.ai_usage_service import UsageMeasurement


class AIUsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, measurement: UsageMeasurement, prompt_tokens: int, completion_tokens: int, input_cost: Decimal, output_cost: Decimal, total_cost: Decimal, equivalent_openai_cost: Decimal) -> AIUsage:
        item = AIUsage(user_id=measurement.user_id, project_id=measurement.project_id, workflow_execution_id=measurement.workflow_execution_id, workflow_step=measurement.workflow_step, agent_id=measurement.agent_id, provider=measurement.provider, model=measurement.model, task=measurement.task, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=prompt_tokens + completion_tokens, estimated_input_cost=input_cost, estimated_output_cost=output_cost, estimated_cost=total_cost, equivalent_openai_cost=equivalent_openai_cost, latency_ms=max(0, measurement.latency_ms), cached_response=measurement.cached_response, request_started_at=measurement.started_at, request_finished_at=measurement.finished_at)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def _filters(*, user_id: UUID, project_id: UUID | None = None, agent_id: UUID | None = None, provider: str | None = None, model: str | None = None, date_from: dt.datetime | None = None, date_to: dt.datetime | None = None) -> list:
        filters = [AIUsage.user_id == user_id]
        if project_id:
            filters.append(AIUsage.project_id == project_id)
        if agent_id:
            filters.append(AIUsage.agent_id == agent_id)
        if provider:
            filters.append(AIUsage.provider == provider)
        if model:
            filters.append(AIUsage.model == model)
        if date_from:
            filters.append(AIUsage.created_at >= date_from)
        if date_to:
            filters.append(AIUsage.created_at <= date_to)
        return filters

    def list(self, *, user_id: UUID, project_id: UUID | None = None, agent_id: UUID | None = None, provider: str | None = None, model: str | None = None, date_from: dt.datetime | None = None, date_to: dt.datetime | None = None) -> list[AIUsage]:
        filters = self._filters(user_id=user_id, project_id=project_id, agent_id=agent_id, provider=provider, model=model, date_from=date_from, date_to=date_to)
        return list(self.db.scalars(select(AIUsage).where(*filters).order_by(AIUsage.created_at.asc())).all())

    def summary(self, *, user_id: UUID, project_id: UUID | None = None, agent_id: UUID | None = None, provider: str | None = None, model: str | None = None, date_from: dt.datetime | None = None, date_to: dt.datetime | None = None) -> dict:
        filters = self._filters(user_id=user_id, project_id=project_id, agent_id=agent_id, provider=provider, model=model, date_from=date_from, date_to=date_to)
        row = self.db.execute(select(func.count(AIUsage.id), func.coalesce(func.sum(AIUsage.total_tokens), 0), func.coalesce(func.sum(AIUsage.estimated_cost), 0), func.coalesce(func.sum(AIUsage.equivalent_openai_cost - AIUsage.estimated_cost), 0), func.coalesce(func.sum(func.cast(AIUsage.cached_response, Integer)), 0), func.coalesce(func.avg(AIUsage.latency_ms), 0)).where(*filters)).one()
        return {"total_requests": int(row[0]), "total_tokens": int(row[1]), "estimated_cost": row[2], "ollama_savings": row[3], "cache_hits": int(row[4]), "average_latency_ms": round(float(row[5]), 2)}
