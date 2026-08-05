from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    event_name: str
    action: str
    actor_id: UUID | None
    project_id: UUID | None
    entity_type: str | None
    entity_id: UUID | None
    correlation_id: UUID | None
    payload: dict
    occurred_at: dt.datetime
    created_at: dt.datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
