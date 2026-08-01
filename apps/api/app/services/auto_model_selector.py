from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.repositories.benchmark_repository import BenchmarkRepository
from app.services.model_router import AITaskType, ModelRoute, ModelRouter


@dataclass(frozen=True)
class AutoModelSelection:
    task: AITaskType
    model: str
    reason: str
    source: str
    sample_size: int
    average_score: float | None
    average_duration_ms: int | None
    used_fallback: bool


class AutoModelSelector:
    """Chooses one production model using task-scoped benchmark history."""

    def __init__(
        self,
        *,
        repository: BenchmarkRepository,
        router: ModelRouter,
        minimum_samples: int = 3,
        minimum_average_score: float = 7.0,
    ) -> None:
        if minimum_samples < 1:
            raise ValueError("minimum_samples must be at least 1")
        if not 0 <= minimum_average_score <= 10:
            raise ValueError("minimum_average_score must be between 0 and 10")
        self.repository = repository
        self.router = router
        self.minimum_samples = minimum_samples
        self.minimum_average_score = minimum_average_score

    def select(self, *, user_id: UUID, task: AITaskType) -> AutoModelSelection:
        candidate = self.repository.best_model(
            user_id=user_id,
            task=task,
            minimum_samples=self.minimum_samples,
            minimum_average_score=self.minimum_average_score,
        )
        if candidate is not None:
            return AutoModelSelection(
                task=task,
                model=candidate["model"],
                reason=(
                    "Modelo selecionado pelo histórico de benchmarks do usuário "
                    f"para a tarefa {task.value} "
                    f"({candidate['executions']} execuções, média {candidate['average_score']:.2f})."
                ),
                source="benchmark_history",
                sample_size=candidate["executions"],
                average_score=candidate["average_score"],
                average_duration_ms=candidate["average_duration_ms"],
                used_fallback=False,
            )

        route: ModelRoute = self.router.route(task)
        return AutoModelSelection(
            task=task,
            model=route.model,
            reason=(
                f"Histórico de benchmarks para a tarefa {task.value} "
                f"insuficiente ou abaixo do limiar; {route.reason}"
            ),
            source="configured_router",
            sample_size=0,
            average_score=None,
            average_duration_ms=None,
            used_fallback=route.used_fallback,
        )
