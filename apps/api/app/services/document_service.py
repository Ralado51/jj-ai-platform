from __future__ import annotations

import hashlib
import re
import uuid
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError

from app.models.asset import Asset
from app.models.enums import AssetType
from app.repositories.asset_repository import AssetRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentListResponse,
    DocumentProcessResponse,
)
from app.services.document_extractor import (
    DocumentExtractionError,
    DocumentExtractor,
    SUPPORTED_EXTRACTION_MIME_TYPES,
)
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
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/csv",
    "text/markdown",
    "text/plain",
}

MIME_TYPE_BY_EXTENSION = {
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".webp": "image/webp",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

GENERIC_UPLOAD_MIME_TYPES = {
    "application/octet-stream",
    "application/x-zip-compressed",
    "binary/octet-stream",
}


class DocumentService:
    def __init__(
        self,
        asset_repository: AssetRepository,
        project_repository: ProjectRepository,
        storage: StorageService,
        extractor: DocumentExtractor | None = None,
    ) -> None:
        self.asset_repository = asset_repository
        self.project_repository = project_repository
        self.storage = storage
        self.extractor = extractor or DocumentExtractor()

    def upload(self, project_id: UUID, file: UploadFile) -> Asset:
        self._get_project(project_id, require_active=True)

        filename = Path(file.filename or "documento").name
        extension = Path(filename).suffix.lower()
        reported_content_type = (file.content_type or "application/octet-stream").lower()
        expected_content_type = MIME_TYPE_BY_EXTENSION.get(extension)

        if reported_content_type in ALLOWED_DOCUMENT_MIME_TYPES:
            content_type = reported_content_type
        elif expected_content_type and reported_content_type in GENERIC_UPLOAD_MIME_TYPES:
            content_type = expected_content_type
        else:
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

        processing_status = (
            "pending" if content_type in SUPPORTED_EXTRACTION_MIME_TYPES else "unsupported"
        )
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
                "processing_status": processing_status,
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

    def list(
        self,
        project_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> DocumentListResponse:
        self._get_project(project_id)
        items = self.asset_repository.list_documents_by_project(
            project_id,
            offset=offset,
            limit=limit,
        )
        total = self.asset_repository.count_documents_by_project(project_id)
        return DocumentListResponse(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )

    def get(self, document_id: UUID) -> Asset:
        document = self.asset_repository.get_document(document_id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado.",
            )
        return document

    def process(self, document_id: UUID) -> DocumentProcessResponse:
        document = self.get(document_id)
        mime_type = document.mime_type or "application/octet-stream"
        if mime_type not in SUPPORTED_EXTRACTION_MIME_TYPES:
            metadata = dict(document.asset_metadata or {})
            metadata["processing_status"] = "unsupported"
            document.asset_metadata = metadata
            self.asset_repository.save(document)
            return DocumentProcessResponse(
                document_id=document.id,
                status="unsupported",
                message="Este formato ainda não possui extração de texto.",
            )

        metadata = dict(document.asset_metadata or {})
        metadata["processing_status"] = "processing"
        metadata.pop("processing_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        source = BytesIO()
        try:
            self.storage.download_file(object_key=document.storage_path, destination=source)
            extracted_text = self.extractor.extract(
                content=source.getvalue(),
                mime_type=mime_type,
            ).strip()
            if not extracted_text:
                raise DocumentExtractionError("No extractable text found.")

            extracted_text_path = f"{document.storage_path}.extracted.txt"
            self.storage.upload_file(
                file_obj=BytesIO(extracted_text.encode("utf-8")),
                object_key=extracted_text_path,
                content_type="text/plain; charset=utf-8",
                metadata={
                    "document-id": str(document.id),
                    "source-sha256": document.checksum or "",
                },
            )
        except (StorageError, DocumentExtractionError) as exc:
            metadata = dict(document.asset_metadata or {})
            metadata["processing_status"] = "failed"
            metadata["processing_error"] = str(exc)
            document.asset_metadata = metadata
            self.asset_repository.save(document)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Não foi possível extrair texto deste documento.",
            ) from exc

        metadata = dict(document.asset_metadata or {})
        metadata.update(
            {
                "processing_status": "processed",
                "extracted_text_path": extracted_text_path,
                "character_count": len(extracted_text),
            }
        )
        metadata.pop("processing_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        return DocumentProcessResponse(
            document_id=document.id,
            status="processed",
            extracted_text_path=extracted_text_path,
            character_count=len(extracted_text),
            message="Texto extraído e armazenado com sucesso.",
        )

    def get_download(self, document_id: UUID) -> DocumentDownloadResponse:
        document = self.get(document_id)
        try:
            url = self.storage.generate_presigned_url(
                object_key=document.storage_path,
                download_filename=document.name,
            )
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível gerar o link de download.",
            ) from exc

        return DocumentDownloadResponse(
            document_id=document.id,
            filename=document.name,
            url=url,
            expires_in=self.storage.presigned_url_expire_seconds,
        )

    def delete(self, document_id: UUID) -> None:
        document = self.get(document_id)
        object_keys = [document.storage_path]
        extracted_text_path = (document.asset_metadata or {}).get("extracted_text_path")
        if isinstance(extracted_text_path, str) and extracted_text_path:
            object_keys.append(extracted_text_path)

        try:
            for object_key in object_keys:
                self.storage.delete_file(object_key=object_key)
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível remover o documento do armazenamento.",
            ) from exc

        try:
            self.asset_repository.delete(document)
        except SQLAlchemyError as exc:
            self.asset_repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="O arquivo foi removido, mas o registro não pôde ser excluído.",
            ) from exc

    def _get_project(self, project_id: UUID, *, require_active: bool = False):
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado.",
            )
        if require_active and not project.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível adicionar documentos a um projeto arquivado.",
            )
        return project

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.")
        return normalized[:180] or "documento"
