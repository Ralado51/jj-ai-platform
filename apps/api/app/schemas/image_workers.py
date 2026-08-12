from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ImageWorkerRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    runtime: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)


class ImageWorkerResponse(BaseModel):
    id: UUID
    name: str
    runtime: str
    model: str
    status: str
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImageWorkerHeartbeatRequest(BaseModel):
    worker_id: UUID


class ImageWorkerClaimRequest(BaseModel):
    worker_id: UUID


class ImageWorkerClaimResponse(BaseModel):
    job_id: UUID | None = None
    project_id: UUID | None = None
    external_id: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt: str | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None


class ImageWorkerResultRequest(BaseModel):
    worker_id: UUID
    image_base64: str = Field(min_length=1)
    mime_type: str = Field(default="image/png", max_length=150)
    seed: int | None = Field(default=None, ge=0)


class ImageWorkerFailedRequest(BaseModel):
    worker_id: UUID
    error: str = Field(min_length=1, max_length=12000)
