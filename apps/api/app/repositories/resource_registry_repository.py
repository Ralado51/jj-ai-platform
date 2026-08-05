from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.resource_registry import ResourceFavorite, ResourceRegistry


class ResourceRegistryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, owner_id: UUID, values: dict) -> ResourceRegistry:
        item = ResourceRegistry(owner_id=owner_id, **values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, *, owner_id: UUID, registry_id: UUID) -> ResourceRegistry | None:
        return self.db.scalar(
            select(ResourceRegistry).where(
                ResourceRegistry.id == registry_id,
                ResourceRegistry.owner_id == owner_id,
            )
        )

    def find_registered(self, *, owner_id: UUID, resource_type: str, resource_id: UUID) -> ResourceRegistry | None:
        return self.db.scalar(
            select(ResourceRegistry).where(
                ResourceRegistry.owner_id == owner_id,
                ResourceRegistry.resource_type == resource_type,
                ResourceRegistry.resource_id == resource_id,
            )
        )

    def update(self, *, item: ResourceRegistry, values: dict) -> ResourceRegistry:
        for key, value in values.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, *, item: ResourceRegistry) -> None:
        self.db.delete(item)
        self.db.commit()

    def list(
        self,
        *,
        owner_id: UUID,
        query: str | None = None,
        resource_type: str | None = None,
        project_id: UUID | None = None,
        status: str | None = None,
        labels: list[str] | None = None,
        favorites_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ResourceRegistry], int]:
        statement = select(ResourceRegistry).where(ResourceRegistry.owner_id == owner_id)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    ResourceRegistry.name.ilike(pattern),
                    ResourceRegistry.description.ilike(pattern),
                    ResourceRegistry.resource_type.ilike(pattern),
                )
            )
        if resource_type:
            statement = statement.where(ResourceRegistry.resource_type == resource_type)
        if project_id:
            statement = statement.where(ResourceRegistry.project_id == project_id)
        if status:
            statement = statement.where(ResourceRegistry.status == status)
        if labels:
            statement = statement.where(ResourceRegistry.labels.overlap(labels))
        if favorites_only:
            statement = statement.join(
                ResourceFavorite,
                (ResourceFavorite.registry_id == ResourceRegistry.id)
                & (ResourceFavorite.user_id == owner_id)
                & ResourceFavorite.is_favorite.is_(True),
            )
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self.db.scalars(
                statement.order_by(ResourceRegistry.updated_at.desc()).offset(offset).limit(limit)
            ).all()
        )
        return items, total

    def favorite_ids(self, *, user_id: UUID, registry_ids: list[UUID]) -> set[UUID]:
        if not registry_ids:
            return set()
        return set(
            self.db.scalars(
                select(ResourceFavorite.registry_id).where(
                    ResourceFavorite.user_id == user_id,
                    ResourceFavorite.registry_id.in_(registry_ids),
                    ResourceFavorite.is_favorite.is_(True),
                )
            ).all()
        )

    def set_favorite(self, *, user_id: UUID, registry_id: UUID, enabled: bool) -> None:
        item = self.db.scalar(
            select(ResourceFavorite).where(
                ResourceFavorite.user_id == user_id,
                ResourceFavorite.registry_id == registry_id,
            )
        )
        if item is None:
            item = ResourceFavorite(user_id=user_id, registry_id=registry_id, is_favorite=enabled)
            self.db.add(item)
        else:
            item.is_favorite = enabled
        self.db.commit()
