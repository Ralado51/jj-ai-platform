from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import HTTPException, status

from app.events.bus import DomainEventBus, domain_event_bus
from app.events.types import WorkflowBenchmarkFinished
from app.models.agent_workflow import AgentWorkflow
from app.models.user import User, UserRole
from app.models.workflow_benchmark import WorkflowBenchmark
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.repositories.workflow_benchmark_repository import WorkflowBenchmarkRepository
from app.schemas.workflow_benchmarks import WorkflowBenchmarkCreate
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator
from app.services.agent_service import AgentService
from app.services.prompt_evaluation_service import PromptEvaluationService


class WorkflowBenchmarkService:
    def __init__(
        self,
        repository: WorkflowBenchmarkRepository,
        version_repository: ResourceVersionRepository,
        *,
        agent_service: AgentService,
        event_bus: DomainEventBus = domain_event_bus,
    ) -> None:
        self.repository = repository
        self.version_repository = version_repository
        self.agent_service = agent_service
        self.event_bus = event_bus

    def run(
        self,
        *,
        workflow: AgentWorkflow,
        payload: WorkflowBenchmarkCreate,
        user: User,
    ) -> WorkflowBenchmark:
        if workflow.user_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para avaliar este workflow.",
            )

        snapshots = {
            version_number: self._get_snapshot(
                workflow=workflow,
                version_number=version_number,
            )
            for version_number in payload.versions
        }
        started_at = perf_counter()
        results: list[dict] = []
        errors: list[str] = []

        for version_number, snapshot in snapshots.items():
            candidate_started_at = perf_counter()
            case_results: list[dict] = []
            for case in payload.cases:
                case_started_at = perf_counter()
                try:
                    outcome = AgentOrchestrator(self.agent_service).run(
                        initial_instruction=case.input,
                        steps=[
                            AgentOrchestrationStep(
                                agent_id=step["agent_id"],
                                instruction=step.get("instruction"),
                            )
                            for step in snapshot["steps"]
                        ],
                        user_id=user.id,
                        project_id=workflow.project_id,
                        session_key=None,
                        use_memory=False,
                    )
                    score, matched, missing = PromptEvaluationService._score(
                        output=outcome.final_content,
                        expected_output=case.expected_output,
                        expected_keywords=case.expected_keywords,
                    )
                    case_results.append(
                        {
                            "name": case.name,
                            "output": outcome.final_content,
                            "score": score,
                            "passed": score >= 0.8,
                            "matched_keywords": matched,
                            "missing_keywords": missing,
                            "duration_ms": outcome.total_duration_ms,
                            "estimated_tokens": self._estimate_tokens(
                                case.input, outcome.final_content
                            ),
                            "error": None,
                        }
                    )
                except Exception as exc:
                    message = str(exc)[:2000]
                    errors.append(f"v{version_number}/{case.name}: {message}")
                    case_results.append(
                        {
                            "name": case.name,
                            "output": "",
                            "score": 0.0,
                            "passed": False,
                            "matched_keywords": [],
                            "missing_keywords": case.expected_keywords,
                            "duration_ms": max(
                                0, round((perf_counter() - case_started_at) * 1000)
                            ),
                            "estimated_tokens": self._estimate_tokens(case.input),
                            "error": message,
                        }
                    )

            average_score = round(
                sum(item["score"] for item in case_results) / len(case_results), 4
            )
            successful_cases = sum(item["error"] is None for item in case_results)
            results.append(
                {
                    "version": version_number,
                    "score": average_score,
                    "success_rate": round(successful_cases / len(case_results), 4),
                    "duration_ms": max(
                        0, round((perf_counter() - candidate_started_at) * 1000)
                    ),
                    "estimated_tokens": sum(
                        item["estimated_tokens"] for item in case_results
                    ),
                    "cases": case_results,
                }
            )

        eligible = [item for item in results if item["success_rate"] > 0]
        winner = (
            max(
                eligible,
                key=lambda item: (
                    item["score"],
                    item["success_rate"],
                    -item["duration_ms"],
                ),
            )["version"]
            if eligible
            else None
        )
        benchmark_status = "completed" if not errors else (
            "partial" if eligible else "failed"
        )
        benchmark = self.repository.create(
            values={
                "owner_id": workflow.user_id,
                "project_id": workflow.project_id,
                "workflow_id": workflow.id,
                "name": payload.name,
                "status": benchmark_status,
                "dataset": [case.model_dump() for case in payload.cases],
                "candidate_versions": payload.versions,
                "results": sorted(
                    results,
                    key=lambda item: (
                        -item["score"],
                        -item["success_rate"],
                        item["duration_ms"],
                    ),
                ),
                "winner_version": winner,
                "duration_ms": max(0, round((perf_counter() - started_at) * 1000)),
                "error": "\n".join(errors)[:2000] if errors else None,
            }
        )
        self.event_bus.publish(
            WorkflowBenchmarkFinished(
                actor_id=user.id,
                project_id=workflow.project_id,
                benchmark_id=benchmark.id,
                workflow_id=workflow.id,
                status=benchmark_status,
                candidate_versions=tuple(payload.versions),
                winner_version=winner,
            )
        )
        return benchmark

    def list(
        self,
        *,
        workflow: AgentWorkflow,
        user: User,
        offset: int,
        limit: int,
    ) -> tuple[list[WorkflowBenchmark], int]:
        if workflow.user_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para consultar este workflow.",
            )
        return self.repository.list(
            owner_id=workflow.user_id,
            workflow_id=workflow.id,
            offset=offset,
            limit=limit,
        )

    def _get_snapshot(
        self,
        *,
        workflow: AgentWorkflow,
        version_number: int,
    ) -> dict:
        version = self.version_repository.get(
            owner_id=workflow.user_id,
            resource_type="workflow",
            resource_id=workflow.id,
            version_number=version_number,
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow version {version_number} not found.",
            )
        snapshot = version.snapshot
        if not snapshot.get("steps"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Workflow version {version_number} has no steps.",
            )
        return snapshot

    @staticmethod
    def _estimate_tokens(*parts: str) -> int:
        return max(1, round(sum(len(part) for part in parts) / 4))
