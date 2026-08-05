from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResourceVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    owner_id: UUID
    project_id: UUID | None
    resource_type: str
    resource_id: UUID
    version_number: int
    snapshot: dict
    checksum: str
    occurred_at: dt.datetime
    created_at: dt.datetime


class ResourceVersionListResponse(BaseModel):
    items: list[ResourceVersionResponse]
    total: int
    page: int
    page_size: int
