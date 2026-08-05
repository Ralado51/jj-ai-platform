from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.resource_version import ResourceVersion


class ResourceVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_once(self, *, values: dict) -> ResourceVersion | None:
        if self.db.scalar(select(ResourceVersion.id).where(ResourceVersion.event_id == values["event_id"])):
            return None
        latest = self.db.scalar(
            select(func.max(ResourceVersion.version_number)).where(
                ResourceVersion.owner_id == values["owner_id"],
                ResourceVersion.resource_type == values["resource_type"],
                ResourceVersion.resource_id == values["resource_id"],
            )
        )
        item = ResourceVersion(version_number=int(latest or 0) + 1, **values)
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return None
        self.db.refresh(item)
        return item

    def list(
        self,
        *,
        owner_id: UUID,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        project_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ResourceVersion], int]:
        statement = select(ResourceVersion).where(ResourceVersion.owner_id == owner_id)
        if resource_type:
            statement = statement.where(ResourceVersion.resource_type == resource_type)
        if resource_id is not None:
            statement = statement.where(ResourceVersion.resource_id == resource_id)
        if project_id is not None:
            statement = statement.where(ResourceVersion.project_id == project_id)
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self.db.scalars(
                statement.order_by(ResourceVersion.occurred_at.desc(), ResourceVersion.version_number.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total

    def get(
        self,
        *,
        owner_id: UUID,
        resource_type: str,
        resource_id: UUID,
        version_number: int,
    ) -> ResourceVersion | None:
        return self.db.scalar(
            select(ResourceVersion).where(
                ResourceVersion.owner_id == owner_id,
                ResourceVersion.resource_type == resource_type,
                ResourceVersion.resource_id == resource_id,
                ResourceVersion.version_number == version_number,
            )
        )
