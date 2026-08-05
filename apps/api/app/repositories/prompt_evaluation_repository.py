from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prompt_evaluation import PromptEvaluation


class PromptEvaluationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, values: dict) -> PromptEvaluation:
        item = PromptEvaluation(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, *, owner_id: UUID, prompt_id: UUID, offset: int = 0, limit: int = 50) -> tuple[list[PromptEvaluation], int]:
        statement = select(PromptEvaluation).where(
            PromptEvaluation.owner_id == owner_id,
            PromptEvaluation.prompt_id == prompt_id,
        )
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self.db.scalars(
                statement.order_by(PromptEvaluation.created_at.desc()).offset(offset).limit(limit)
            ).all()
        )
        return items, total

    def get(self, *, owner_id: UUID, evaluation_id: UUID) -> PromptEvaluation | None:
        return self.db.scalar(
            select(PromptEvaluation).where(
                PromptEvaluation.owner_id == owner_id,
                PromptEvaluation.id == evaluation_id,
            )
        )
