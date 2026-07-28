from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AssetType


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    asset_type: AssetType
    name: str
    description: str | None
    storage_provider: str
    storage_path: str
    public_url: str | None
    mime_type: str | None
    size_bytes: int | None
    checksum: str | None
    asset_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    offset: int
    limit: int


class DocumentDownloadResponse(BaseModel):
    document_id: UUID
    filename: str
    url: str
    expires_in: int


class DocumentProcessResponse(BaseModel):
    document_id: UUID
    status: str
    extracted_text_path: str | None = None
    character_count: int = 0
    message: str
