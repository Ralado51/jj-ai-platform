from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ResourceUpserted(DomainEvent):
    owner_id: UUID
    resource_type: str
    resource_id: UUID
    name: str
    description: str | None = None
    project_id: UUID | None = None
    status: str = "active"
    labels: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ResourceRemoved(DomainEvent):
    owner_id: UUID
    resource_type: str
    resource_id: UUID
