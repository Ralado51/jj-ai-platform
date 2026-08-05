from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.workflow_benchmark import WorkflowBenchmark


class WorkflowBenchmarkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, values: dict) -> WorkflowBenchmark:
        item = WorkflowBenchmark(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(
        self,
        *,
        owner_id: UUID,
        workflow_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WorkflowBenchmark], int]:
        statement = select(WorkflowBenchmark).where(
            WorkflowBenchmark.owner_id == owner_id,
            WorkflowBenchmark.workflow_id == workflow_id,
        )
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self.db.scalars(
                statement.order_by(WorkflowBenchmark.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total
