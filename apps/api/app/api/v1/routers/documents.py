from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.asset_repository import AssetRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import (
    DocumentChunkResponse,
    DocumentDownloadResponse,
    DocumentEmbeddingResponse,
    DocumentListResponse,
    DocumentProcessResponse,
    DocumentResponse,
)
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.storage import StorageService, get_storage_service

project_documents_router = APIRouter(
    prefix="/projects/{project_id}/documents",
    tags=["documents"],
)
documents_router = APIRouter(prefix="/documents", tags=["documents"])


def get_service(
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(
        asset_repository=AssetRepository(db),
        project_repository=ProjectRepository(db),
        storage=storage,
    )


def get_embedding_service(db: Session = Depends(get_db)) -> EmbeddingService:
    return EmbeddingService(asset_repository=AssetRepository(db))


@project_documents_router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> DocumentResponse:
    return service.upload(project_id, file)


@project_documents_router.get("", response_model=DocumentListResponse)
def list_documents(
    project_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: DocumentService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> DocumentListResponse:
    return service.list(project_id, offset=offset, limit=limit)


@documents_router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> DocumentResponse:
    return service.get(document_id)


@documents_router.post(
    "/{document_id}/process",
    response_model=DocumentProcessResponse,
)
def process_document(
    document_id: UUID,
    service: DocumentService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> DocumentProcessResponse:
    return service.process(document_id)


@documents_router.post(
    "/{document_id}/embeddings",
    response_model=DocumentEmbeddingResponse,
)
def generate_document_embeddings(
    document_id: UUID,
    service: EmbeddingService = Depends(get_embedding_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> DocumentEmbeddingResponse:
    return service.embed_document(document_id)


@documents_router.get(
    "/{document_id}/chunks",
    response_model=list[DocumentChunkResponse],
)
def list_document_chunks(
    document_id: UUID,
    service: DocumentService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[DocumentChunkResponse]:
    return service.list_chunks(document_id)


@documents_router.get(
    "/{document_id}/download",
    response_model=DocumentDownloadResponse,
)
def download_document(
    document_id: UUID,
    service: DocumentService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> DocumentDownloadResponse:
    return service.get_download(document_id)


@documents_router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: UUID,
    service: DocumentService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> Response:
    service.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router = project_documents_router
