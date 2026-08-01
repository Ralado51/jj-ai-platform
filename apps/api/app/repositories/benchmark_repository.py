from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.benchmark_run import BenchmarkResult, BenchmarkRun
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse


class BenchmarkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, *, user_id: UUID, payload: BenchmarkRunRequest, result: BenchmarkRunResponse) -> BenchmarkRun:
        run = BenchmarkRun(
            user_id=user_id,
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            winner=result.winner,
            models=payload.models,
        )
        self.db.add(run)
        self.db.flush()

        for item in result.results:
            scores = item.scores.model_dump() if item.scores is not None else None
            self.db.add(
                BenchmarkResult(
                    run_id=run.id,
                    model=item.model,
                    duration_ms=item.duration_ms,
                    estimated_tokens=item.estimated_tokens,
                    success=item.success,
                    error=item.error,
                    overall=item.scores.overall if item.scores is not None else None,
                    scores=scores,
                )
            )

        self.db.commit()
        self.db.refresh(run)
        return run

    def best_model(
        self,
        *,
        user_id: UUID,
        minimum_samples: int,
        minimum_average_score: float,
    ) -> dict | None:
        row = self.db.execute(
            select(
                BenchmarkResult.model,
                func.count(BenchmarkResult.id).label("executions"),
                func.avg(BenchmarkResult.overall).label("average_score"),
                func.avg(BenchmarkResult.duration_ms).label("average_duration_ms"),
            )
            .join(BenchmarkRun, BenchmarkRun.id == BenchmarkResult.run_id)
            .where(
                BenchmarkRun.user_id == user_id,
                BenchmarkResult.success.is_(True),
                BenchmarkResult.overall.is_not(None),
            )
            .group_by(BenchmarkResult.model)
            .having(func.count(BenchmarkResult.id) >= minimum_samples)
            .having(func.avg(BenchmarkResult.overall) >= minimum_average_score)
            .order_by(
                desc(func.avg(BenchmarkResult.overall)),
                func.avg(BenchmarkResult.duration_ms),
            )
            .limit(1)
        ).first()
        if row is None:
            return None
        return {
            "model": row.model,
            "executions": int(row.executions),
            "average_score": round(float(row.average_score), 2),
            "average_duration_ms": round(float(row.average_duration_ms or 0)),
        }

    def summary(self, *, user_id: UUID) -> dict:
        total_runs = self.db.scalar(
            select(func.count(BenchmarkRun.id)).where(BenchmarkRun.user_id == user_id)
        ) or 0
        total_results = self.db.scalar(
            select(func.count(BenchmarkResult.id))
            .join(BenchmarkRun, BenchmarkRun.id == BenchmarkResult.run_id)
            .where(BenchmarkRun.user_id == user_id)
        ) or 0
        success_count = self.db.scalar(
            select(func.count(BenchmarkResult.id))
            .join(BenchmarkRun, BenchmarkRun.id == BenchmarkResult.run_id)
            .where(BenchmarkRun.user_id == user_id, BenchmarkResult.success.is_(True))
        ) or 0

        rows = self.db.execute(
            select(
                BenchmarkResult.model,
                func.count(BenchmarkResult.id),
                func.avg(BenchmarkResult.overall),
                func.avg(BenchmarkResult.duration_ms),
                func.sum(BenchmarkResult.estimated_tokens),
            )
            .join(BenchmarkRun, BenchmarkRun.id == BenchmarkResult.run_id)
            .where(BenchmarkRun.user_id == user_id, BenchmarkResult.success.is_(True))
            .group_by(BenchmarkResult.model)
            .order_by(desc(func.avg(BenchmarkResult.overall)))
        ).all()

        winner_rows = self.db.execute(
            select(BenchmarkRun.winner, func.count(BenchmarkRun.id))
            .where(BenchmarkRun.user_id == user_id, BenchmarkRun.winner.is_not(None))
            .group_by(BenchmarkRun.winner)
            .order_by(desc(func.count(BenchmarkRun.id)))
        ).all()

        return {
            "total_runs": total_runs,
            "total_results": total_results,
            "success_rate": round((success_count / total_results) * 100, 2) if total_results else 0.0,
            "top_model": rows[0][0] if rows else None,
            "models": [
                {
                    "model": model,
                    "executions": executions,
                    "average_score": round(float(avg_score or 0), 2),
                    "average_duration_ms": round(float(avg_duration or 0)),
                    "estimated_tokens": int(tokens or 0),
                }
                for model, executions, avg_score, avg_duration, tokens in rows
            ],
            "winners": [
                {"model": model, "wins": wins}
                for model, wins in winner_rows
                if model is not None
            ],
        }
