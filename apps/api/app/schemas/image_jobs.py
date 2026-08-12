from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ImageJobStatus = Literal[
    "pending",
    "processing",
    "generated",
    "approved",
    "rejected",
    "failed",
]


class ImageJobCreate(BaseModel):
    project_id: UUID
    external_id: str | None = Field(default=None, max_length=200)
    provider: str = Field(default="free-worker", min_length=1, max_length=80)
    model: str = Field(default="Z-Image-Turbo", min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=12000)
    width: int = Field(default=1344, ge=256, le=4096)
    height: int = Field(default=768, ge=256, le=4096)
    seed: int | None = Field(default=None, ge=0)


class ImageJobBatchCreate(BaseModel):
    items: list[ImageJobCreate] = Field(min_length=1, max_length=100)


class ImageJobResponse(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    external_id: str | None
    provider: str
    model: str
    prompt: str
    width: int
    height: int
    seed: int | None
    status: ImageJobStatus
    worker_id: str | None
    asset_id: UUID | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImageJobBatchResponse(BaseModel):
    total: int
    jobs: list[ImageJobResponse]


class ImageJobReviewRequest(BaseModel):
    action: Literal["approve", "reject", "regenerate"]
