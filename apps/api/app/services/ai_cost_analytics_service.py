from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from app.repositories.ai_usage_repository import AIUsageRepository


class AICostAnalyticsService:
    def __init__(self, repository: AIUsageRepository) -> None:
        self.repository = repository

    @staticmethod
    def _growth(current: Decimal | int, previous: Decimal | int) -> float:
        current_value = float(current)
        previous_value = float(previous)
        if previous_value == 0:
            return 100.0 if current_value > 0 else 0.0
        return round(((current_value - previous_value) / previous_value) * 100, 2)

    def dashboard(self, *, user_id: UUID, project_id: UUID | None = None, agent_id: UUID | None = None, provider: str | None = None, model: str | None = None, date_from: dt.datetime | None = None, date_to: dt.datetime | None = None) -> dict:
        items = self.repository.list(user_id=user_id, project_id=project_id, agent_id=agent_id, provider=provider, model=model, date_from=date_from, date_to=date_to)

        timeline: dict[dt.date, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0"), "savings": Decimal("0")})
        providers: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0"), "latency": 0})
        models: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0"), "latency": 0})
        agents: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0")})
        projects: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0")})
        workflows: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": Decimal("0")})

        total_cost = Decimal("0")
        total_savings = Decimal("0")
        total_tokens = 0
        total_latency = 0
        cache_hits = 0

        for item in items:
            day = item.created_at.date()
            cost = Decimal(item.estimated_cost or 0)
            equivalent = Decimal(item.equivalent_openai_cost or 0)
            savings = max(Decimal("0"), equivalent - cost)
            tokens = int(item.total_tokens or 0)
            latency = int(item.latency_ms or 0)

            total_cost += cost
            total_savings += savings
            total_tokens += tokens
            total_latency += latency
            cache_hits += int(bool(item.cached_response))

            timeline[day]["requests"] += 1
            timeline[day]["tokens"] += tokens
            timeline[day]["cost"] += cost
            timeline[day]["savings"] += savings

            for key, collection in ((item.provider or "unknown", providers), (item.model or "unknown", models)):
                collection[key]["requests"] += 1
                collection[key]["tokens"] += tokens
                collection[key]["cost"] += cost
                collection[key]["latency"] += latency

            if item.agent_id:
                key = str(item.agent_id)
                agents[key]["requests"] += 1
                agents[key]["tokens"] += tokens
                agents[key]["cost"] += cost
            if item.project_id:
                key = str(item.project_id)
                projects[key]["requests"] += 1
                projects[key]["tokens"] += tokens
                projects[key]["cost"] += cost
            if item.workflow_execution_id:
                key = str(item.workflow_execution_id)
                workflows[key]["requests"] += 1
                workflows[key]["tokens"] += tokens
                workflows[key]["cost"] += cost

        ordered_days = sorted(timeline)
        midpoint = max(0, len(ordered_days) - 7)
        current_days = set(ordered_days[midpoint:])
        previous_days = set(ordered_days[max(0, midpoint - 7):midpoint])

        def period_sum(days: set[dt.date], field: str):
            return sum((timeline[day][field] for day in days), Decimal("0") if field in {"cost", "savings"} else 0)

        summary = {
            "total_requests": len(items),
            "total_tokens": total_tokens,
            "estimated_cost": total_cost,
            "ollama_savings": total_savings,
            "cache_hits": cache_hits,
            "cache_hit_rate": round((cache_hits / len(items)) * 100, 2) if items else 0.0,
            "average_latency_ms": round(total_latency / len(items), 2) if items else 0.0,
        }
        trends = {
            "weekly_request_growth": self._growth(period_sum(current_days, "requests"), period_sum(previous_days, "requests")),
            "weekly_token_growth": self._growth(period_sum(current_days, "tokens"), period_sum(previous_days, "tokens")),
            "weekly_cost_growth": self._growth(period_sum(current_days, "cost"), period_sum(previous_days, "cost")),
        }

        def ranked(collection: dict[str, dict], *, include_latency: bool = False) -> list[dict]:
            result = []
            for key, values in collection.items():
                row = {"key": key, "requests": values["requests"], "tokens": values["tokens"], "cost": values["cost"]}
                if include_latency:
                    row["average_latency_ms"] = round(values["latency"] / values["requests"], 2)
                result.append(row)
            return sorted(result, key=lambda row: (row["cost"], row["tokens"]), reverse=True)

        return {
            "summary": summary,
            "trends": trends,
            "timeline": [{"date": day, **timeline[day]} for day in ordered_days],
            "providers": ranked(providers, include_latency=True),
            "models": ranked(models, include_latency=True),
            "agents": ranked(agents),
            "projects": ranked(projects),
            "workflows": ranked(workflows),
        }
