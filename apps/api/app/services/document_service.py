from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError

from app.models.asset import Asset
from app.models.enums import AssetType
from app.repositories.asset_repository import AssetRepository
from app.repositories.project_repository import ProjectRepository
from app.services.storage import StorageError, StorageService

MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/json",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/csv",
    "text/markdown",
    "text/plain",
}


class DocumentService:
    def __init__(
        self,
        asset_repository: AssetRepository,
        project_repository: ProjectRepository,
        storage: StorageService,
    ) -> None:
        self.asset_repository = asset_repository
        self.project_repository = project_repository
        self.storage = storage

    def upload(self, project_id: UUID, file: UploadFile) -> Asset:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado.",
            )
        if not project.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível adicionar documentos a um projeto arquivado.",
            )

        filename = Path(file.filename or "documento").name
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Tipo de arquivo não permitido.",
            )

        content = file.file.read(MAX_DOCUMENT_SIZE_BYTES + 1)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo está vazio.",
            )
        if len(content) > MAX_DOCUMENT_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="O arquivo excede o limite de 25 MB.",
            )

        checksum = hashlib.sha256(content).hexdigest()
        safe_filename = self._sanitize_filename(filename)
        object_key = f"projects/{project_id}/documents/{uuid.uuid4()}-{safe_filename}"

        from io import BytesIO

        try:
            self.storage.upload_file(
                file_obj=BytesIO(content),
                object_key=object_key,
                content_type=content_type,
                metadata={
                    "project-id": str(project_id),
                    "original-filename": filename,
                    "sha256": checksum,
                },
            )
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível armazenar o documento.",
            ) from exc

        asset = Asset(
            project_id=project_id,
            asset_type=AssetType.DOCUMENT,
            name=filename,
            storage_provider="s3",
            storage_path=object_key,
            mime_type=content_type,
            size_bytes=len(content),
            checksum=checksum,
            asset_metadata={
                "status": "uploaded",
                "original_filename": filename,
            },
        )

        try:
            return self.asset_repository.create(asset)
        except SQLAlchemyError as exc:
            self.asset_repository.db.rollback()
            try:
                self.storage.delete_file(object_key=object_key)
            except StorageError:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="O arquivo foi recebido, mas não foi possível registrar o documento.",
            ) from exc

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.")
        return normalized[:180] or "documento"
