from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.schemas.analytics import (
    WorkflowInsightResponse,
    WorkflowInsightsResponse,
    WorkflowRecommendationResponse,
)


class WorkflowInsightsService:
    TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

    def __init__(self, repository: WorkflowExecutionRepository) -> None:
        self.repository = repository

    def insights(self, *, user_id: UUID, workflow_id: UUID | None = None) -> WorkflowInsightsResponse:
        executions = self.repository.list(user_id=user_id, workflow_id=workflow_id, limit=1000)
        grouped: dict[UUID, list] = defaultdict(list)
        for execution in executions:
            grouped[execution.workflow_id].append(execution)

        items = [self._build_workflow_insight(group) for group in grouped.values()]
        items.sort(key=lambda item: item.health_score)
        return WorkflowInsightsResponse(workflows=items)

    def _build_workflow_insight(self, executions: list) -> WorkflowInsightResponse:
        terminal = [item for item in executions if item.status in self.TERMINAL_STATUSES]
        completed = [item for item in terminal if item.status == "completed"]
        retries = [item for item in executions if item.parent_execution_id is not None]
        success_rate = (len(completed) / len(terminal) * 100) if terminal else 0.0
        retry_rate = (len(retries) / len(executions) * 100) if executions else 0.0
        average_duration = round(sum(item.total_duration_ms for item in completed) / len(completed)) if completed else 0

        step_durations: dict[int, list[int]] = defaultdict(list)
        step_agents: dict[int, tuple[str, str | None]] = {}
        total_step_duration = 0
        for execution in completed:
            for detail in execution.step_details or []:
                position = int(detail.get("index", 0))
                duration = int(detail.get("duration_ms", 0))
                if position <= 0:
                    continue
                step_durations[position].append(duration)
                total_step_duration += duration
                step_agents[position] = (
                    str(detail.get("agent_id", "unknown")),
                    str(detail.get("model")) if detail.get("model") else None,
                )

        averages = {
            position: round(sum(values) / len(values))
            for position, values in step_durations.items()
            if values
        }
        bottleneck_step = max(averages, key=averages.get) if averages else None
        bottleneck_share = (
            round((sum(step_durations[bottleneck_step]) / total_step_duration) * 100, 2)
            if bottleneck_step and total_step_duration
            else None
        )

        score = 100
        score -= round((100 - success_rate) * 0.55)
        score -= round(min(retry_rate, 50) * 0.35)
        if bottleneck_share and bottleneck_share >= 60:
            score -= 10
        elif bottleneck_share and bottleneck_share >= 45:
            score -= 5
        if len(terminal) < 3:
            score -= 5
        score = max(0, min(100, score))

        recommendations: list[WorkflowRecommendationResponse] = []
        if success_rate < 80:
            recommendations.append(WorkflowRecommendationResponse(
                code="low_success_rate",
                severity="critical" if success_rate < 60 else "warning",
                title="Taxa de sucesso abaixo do esperado",
                description=f"O workflow concluiu {success_rate:.1f}% das execuções terminais.",
                action="Revise os pontos de falha e adicione validação ou fallback nas etapas instáveis.",
            ))
        if retry_rate >= 20:
            recommendations.append(WorkflowRecommendationResponse(
                code="high_retry_rate",
                severity="warning",
                title="Retries acima da média",
                description=f"{retry_rate:.1f}% das execuções são reexecuções.",
                action="Corrija a etapa recorrente antes de aumentar tentativas automáticas.",
            ))
        if bottleneck_step and bottleneck_share and bottleneck_share >= 45:
            agent_id, model = step_agents.get(bottleneck_step, (None, None))
            recommendations.append(WorkflowRecommendationResponse(
                code="step_bottleneck",
                severity="warning",
                title=f"Etapa {bottleneck_step} é o principal gargalo",
                description=f"A etapa representa {bottleneck_share:.1f}% do tempo medido.",
                action="Avalie um modelo mais rápido, cache ou paralelização desta etapa.",
                step=bottleneck_step,
                agent_id=agent_id,
                model=model,
            ))
        if len(executions) < 3:
            recommendations.append(WorkflowRecommendationResponse(
                code="insufficient_history",
                severity="info",
                title="Histórico insuficiente",
                description="Ainda não há amostra suficiente para recomendações confiáveis.",
                action="Execute o workflow ao menos três vezes antes de aplicar otimizações.",
            ))
        if not recommendations:
            recommendations.append(WorkflowRecommendationResponse(
                code="healthy_workflow",
                severity="success",
                title="Workflow saudável",
                description="Não foram encontrados gargalos ou padrões críticos no histórico atual.",
                action="Continue monitorando após alterações de prompt, modelo ou ordem das etapas.",
            ))

        label = "Excelente" if score >= 90 else "Bom" if score >= 75 else "Atenção" if score >= 60 else "Crítico"
        first = executions[0]
        return WorkflowInsightResponse(
            workflow_id=first.workflow_id,
            workflow_name=first.workflow_name,
            health_score=score,
            health_label=label,
            executions=len(executions),
            success_rate=round(success_rate, 2),
            retry_rate=round(retry_rate, 2),
            average_duration_ms=average_duration,
            bottleneck_step=bottleneck_step,
            bottleneck_share=bottleneck_share,
            recommendations=recommendations,
        )
