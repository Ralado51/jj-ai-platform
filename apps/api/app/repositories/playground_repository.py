from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.playground import PlaygroundRun, PlaygroundSession


class PlaygroundRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(
        self, *, owner_id: UUID, project_id: UUID | None, name: str
    ) -> PlaygroundSession:
        item = PlaygroundSession(
            owner_id=owner_id, project_id=project_id, name=name
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_session(
        self, *, session_id: UUID, owner_id: UUID
    ) -> PlaygroundSession | None:
        return self.db.scalar(
            select(PlaygroundSession).where(
                PlaygroundSession.id == session_id,
                PlaygroundSession.owner_id == owner_id,
                PlaygroundSession.is_active.is_(True),
            )
        )

    def list_sessions(
        self, *, owner_id: UUID, offset: int, limit: int
    ) -> list[PlaygroundSession]:
        return list(
            self.db.scalars(
                select(PlaygroundSession)
                .where(
                    PlaygroundSession.owner_id == owner_id,
                    PlaygroundSession.is_active.is_(True),
                )
                .order_by(PlaygroundSession.updated_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def create_run(self, *, values: dict) -> PlaygroundRun:
        item = PlaygroundRun(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_runs(
        self, *, session_id: UUID, owner_id: UUID, offset: int, limit: int
    ) -> list[PlaygroundRun]:
        return list(
            self.db.scalars(
                select(PlaygroundRun)
                .where(
                    PlaygroundRun.session_id == session_id,
                    PlaygroundRun.owner_id == owner_id,
                )
                .order_by(PlaygroundRun.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
