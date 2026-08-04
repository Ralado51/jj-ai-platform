from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from app.repositories.ai_usage_repository import AIUsageRepository
from app.services.ai_cost_analytics_service import AICostAnalyticsService


_MONEY = Decimal("0.000001")


class AICostOptimizerService:
    """Generate deterministic, explainable recommendations from AI usage history."""

    def __init__(self, repository: AIUsageRepository) -> None:
        self.repository = repository

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return max(Decimal("0"), value).quantize(_MONEY, rounding=ROUND_HALF_UP)

    def recommendations(
        self,
        *,
        user_id: UUID,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
        date_from: dt.datetime | None = None,
        date_to: dt.datetime | None = None,
    ) -> dict:
        items = self.repository.list(
            user_id=user_id,
            project_id=project_id,
            agent_id=agent_id,
            provider=provider,
            model=model,
            date_from=date_from,
            date_to=date_to,
        )
        if not items:
            return {"potential_monthly_savings": Decimal("0"), "recommendations": []}

        dashboard = AICostAnalyticsService(self.repository).dashboard(
            user_id=user_id,
            project_id=project_id,
            agent_id=agent_id,
            provider=provider,
            model=model,
            date_from=date_from,
            date_to=date_to,
        )
        summary = dashboard["summary"]
        trends = dashboard["trends"]
        total_requests = int(summary["total_requests"])
        total_cost = Decimal(summary["estimated_cost"] or 0)
        cache_rate = float(summary["cache_hit_rate"])
        average_latency = float(summary["average_latency_ms"])

        model_costs: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        provider_costs: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in items:
            cost = Decimal(item.estimated_cost or 0)
            model_costs[item.model or "unknown"] += cost
            provider_costs[(item.provider or "unknown").lower()] += cost

        recommendations: list[dict] = []

        if total_requests >= 10 and cache_rate < 20:
            savings = self._money(total_cost * Decimal("0.15"))
            recommendations.append(
                {
                    "id": "increase-cache-coverage",
                    "priority": "high" if total_requests >= 100 else "medium",
                    "category": "cache",
                    "title": "Aumentar a cobertura de cache",
                    "description": f"A taxa de cache está em {cache_rate:.1f}% para {total_requests} chamadas. Identifique prompts repetitivos e aplique cache nas etapas determinísticas.",
                    "action": "Mapear prompts repetidos e habilitar cache com expiração adequada.",
                    "estimated_monthly_savings": savings,
                    "confidence": 0.8,
                    "evidence": {"cache_hit_rate": cache_rate, "total_requests": total_requests},
                }
            )

        if total_cost > 0 and model_costs:
            top_model, top_cost = max(model_costs.items(), key=lambda item: item[1])
            share = float((top_cost / total_cost) * 100) if total_cost else 0.0
            if share >= 50:
                savings = self._money(top_cost * Decimal("0.25"))
                recommendations.append(
                    {
                        "id": f"benchmark-model-{top_model}",
                        "priority": "high" if share >= 75 else "medium",
                        "category": "model",
                        "title": f"Reavaliar o modelo {top_model}",
                        "description": f"Esse modelo concentra {share:.1f}% do custo do período. Execute um benchmark com modelos menores ou locais antes de alterar produção.",
                        "action": "Comparar qualidade, latência e custo no Benchmark e promover o vencedor somente após atingir a nota mínima.",
                        "estimated_monthly_savings": savings,
                        "confidence": 0.72,
                        "evidence": {"model": top_model, "cost_share": round(share, 2), "current_cost": top_cost},
                    }
                )

        uses_ollama = any(name == "ollama" for name in provider_costs)
        paid_cost = sum((cost for name, cost in provider_costs.items() if name != "ollama"), Decimal("0"))
        if paid_cost > 0 and not uses_ollama:
            savings = self._money(paid_cost * Decimal("0.40"))
            recommendations.append(
                {
                    "id": "pilot-local-model",
                    "priority": "medium",
                    "category": "provider",
                    "title": "Validar uma rota com modelo local",
                    "description": "Não há chamadas Ollama no recorte, embora existam custos com provedores pagos. Um piloto controlado pode reduzir custo sem substituir tarefas críticas automaticamente.",
                    "action": "Executar benchmark com Ollama em uma tarefa de baixo risco e comparar a nota mínima exigida.",
                    "estimated_monthly_savings": savings,
                    "confidence": 0.6,
                    "evidence": {"paid_provider_cost": paid_cost},
                }
            )

        if average_latency >= 2000:
            recommendations.append(
                {
                    "id": "reduce-average-latency",
                    "priority": "high" if average_latency >= 5000 else "medium",
                    "category": "latency",
                    "title": "Reduzir a latência média",
                    "description": f"A latência média está em {average_latency / 1000:.2f}s. Revise o modelo mais lento, o tamanho do contexto e etapas que podem usar cache.",
                    "action": "Comparar modelos equivalentes e limitar contexto desnecessário antes de paralelizar etapas.",
                    "estimated_monthly_savings": Decimal("0"),
                    "confidence": 0.85,
                    "evidence": {"average_latency_ms": average_latency},
                }
            )

        weekly_growth = float(trends["weekly_cost_growth"])
        if weekly_growth >= 20 and total_cost > 0:
            recommendations.append(
                {
                    "id": "investigate-cost-growth",
                    "priority": "high" if weekly_growth >= 50 else "medium",
                    "category": "trend",
                    "title": "Investigar crescimento semanal de custo",
                    "description": f"O custo cresceu {weekly_growth:.1f}% em relação ao período anterior. Confirme se o aumento veio de volume esperado, retries ou mudança de modelo.",
                    "action": "Revisar o ranking por modelo, agente e workflow antes de definir limites de orçamento.",
                    "estimated_monthly_savings": Decimal("0"),
                    "confidence": 0.9,
                    "evidence": {"weekly_cost_growth": weekly_growth},
                }
            )

        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda item: (
                priority_order[item["priority"]],
                -float(item["estimated_monthly_savings"]),
            )
        )
        potential = self._money(sum((Decimal(item["estimated_monthly_savings"]) for item in recommendations), Decimal("0")))
        return {"potential_monthly_savings": potential, "recommendations": recommendations}
