from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    severity: str
    title: str
    message: str
    workflow_id: UUID | None = None
    is_read: bool
    read_at: dt.datetime | None = None
    created_at: dt.datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class NotificationMarkAllReadResponse(BaseModel):
    updated: int
