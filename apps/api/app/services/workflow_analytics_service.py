from __future__ import annotations

from collections import Counter, defaultdict
from uuid import UUID

from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.schemas.analytics import (
    WorkflowAnalyticsResponse,
    WorkflowFailurePointResponse,
    WorkflowPerformanceResponse,
    WorkflowStepPerformanceResponse,
)


class WorkflowAnalyticsService:
    TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

    def __init__(self, repository: WorkflowExecutionRepository) -> None:
        self.repository = repository

    def summary(self, *, user_id: UUID, workflow_id: UUID | None = None) -> WorkflowAnalyticsResponse:
        executions = self.repository.list(user_id=user_id, workflow_id=workflow_id, limit=1000)
        terminal = [item for item in executions if item.status in self.TERMINAL_STATUSES]
        completed = [item for item in terminal if item.status == "completed"]
        failed = [item for item in terminal if item.status == "failed"]
        cancelled = [item for item in terminal if item.status == "cancelled"]
        retries = [item for item in executions if item.parent_execution_id is not None]

        workflow_stats: dict[UUID, dict[str, object]] = defaultdict(
            lambda: {"name": "", "runs": 0, "completed": 0, "duration": 0}
        )
        step_stats: dict[tuple[str, str, int], dict[str, int | str]] = defaultdict(
            lambda: {"runs": 0, "duration": 0, "failures": 0, "agent_name": ""}
        )
        failure_points: Counter[tuple[str, int, str]] = Counter()

        for execution in executions:
            stats = workflow_stats[execution.workflow_id]
            stats["name"] = execution.workflow_name
            stats["runs"] = int(stats["runs"]) + 1
            if execution.status == "completed":
                stats["completed"] = int(stats["completed"]) + 1
                stats["duration"] = int(stats["duration"]) + execution.total_duration_ms

            for detail in execution.step_details or []:
                position = int(detail.get("index", 0))
                agent_id = str(detail.get("agent_id", "unknown"))
                agent_name = str(detail.get("agent_name", agent_id))
                key = (agent_id, agent_name, position)
                item = step_stats[key]
                item["agent_name"] = agent_name
                item["runs"] = int(item["runs"]) + 1
                item["duration"] = int(item["duration"]) + int(detail.get("duration_ms", 0))

            if execution.status == "failed":
                position = min(execution.steps_completed + 1, execution.steps_total)
                failure_points[(execution.workflow_name, position, execution.error_message or "Erro não informado")] += 1

        workflows = [
            WorkflowPerformanceResponse(
                workflow_id=workflow_key,
                workflow_name=str(stats["name"]),
                executions=int(stats["runs"]),
                success_rate=round((int(stats["completed"]) / int(stats["runs"])) * 100, 2)
                if int(stats["runs"])
                else 0.0,
                average_duration_ms=round(int(stats["duration"]) / int(stats["completed"]))
                if int(stats["completed"])
                else 0,
            )
            for workflow_key, stats in workflow_stats.items()
        ]
        workflows.sort(key=lambda item: item.executions, reverse=True)

        steps = [
            WorkflowStepPerformanceResponse(
                agent_id=agent_id,
                agent_name=agent_name,
                position=position,
                executions=int(stats["runs"]),
                average_duration_ms=round(int(stats["duration"]) / int(stats["runs"]))
                if int(stats["runs"])
                else 0,
            )
            for (agent_id, agent_name, position), stats in step_stats.items()
        ]
        steps.sort(key=lambda item: item.average_duration_ms, reverse=True)

        failures = [
            WorkflowFailurePointResponse(
                workflow_name=name,
                step=step,
                occurrences=count,
                error_message=message,
            )
            for (name, step, message), count in failure_points.most_common(10)
        ]

        return WorkflowAnalyticsResponse(
            total_executions=len(executions),
            terminal_executions=len(terminal),
            completed_executions=len(completed),
            failed_executions=len(failed),
            cancelled_executions=len(cancelled),
            retry_executions=len(retries),
            success_rate=round((len(completed) / len(terminal)) * 100, 2) if terminal else 0.0,
            average_duration_ms=round(sum(item.total_duration_ms for item in completed) / len(completed))
            if completed
            else 0,
            workflows=workflows,
            slowest_steps=steps[:10],
            failure_points=failures,
        )
