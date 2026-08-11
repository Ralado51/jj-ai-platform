from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ImageProviderName = Literal["huggingface", "google"]


class ImageGenerationRequest(BaseModel):
    provider: ImageProviderName = "huggingface"
    model: str | None = None
    prompt: str = Field(min_length=1, max_length=12000)
    width: int = Field(default=1344, ge=256, le=4096)
    height: int = Field(default=768, ge=256, le=4096)
    seed: int | None = Field(default=None, ge=0)


class ImageGenerationResponse(BaseModel):
    provider: ImageProviderName
    model: str
    mime_type: str
    image_base64: str
    seed: int | None = None
    latency_ms: int


class BatchImageGenerationItem(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=12000)
    model: str | None = None
    width: int = Field(default=1344, ge=256, le=4096)
    height: int = Field(default=768, ge=256, le=4096)
    seed: int | None = Field(default=None, ge=0)


class BatchImageGenerationRequest(BaseModel):
    provider: ImageProviderName = "huggingface"
    items: list[BatchImageGenerationItem] = Field(min_length=1, max_length=50)


class BatchImageGenerationResult(BaseModel):
    id: str
    status: Literal["completed", "failed"]
    image: ImageGenerationResponse | None = None
    error: str | None = None


class BatchImageGenerationResponse(BaseModel):
    provider: ImageProviderName
    total: int
    completed: int
    failed: int
    results: list[BatchImageGenerationResult]
