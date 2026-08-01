import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.asset_repository import AssetRepository
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import (
    DocumentChunkResponse,
    DocumentDownloadResponse,
    DocumentEmbeddingResponse,
    DocumentListResponse,
    DocumentProcessResponse,
    DocumentResponse,
)
from app.schemas.search import (
    RagAnswerRequest,
    RagAnswerResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.auto_model_rag_service import AutoModelRagService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SemanticSearchService
from app.services.storage import StorageService, get_storage_service

project_documents_router = APIRouter(
    prefix="/projects/{project_id}/documents",
    tags=["documents"],
)
project_search_router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["search"],
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


def get_search_service(db: Session = Depends(get_db)) -> SemanticSearchService:
    embedding_service = EmbeddingService(asset_repository=AssetRepository(db))
    return SemanticSearchService(
        project_repository=ProjectRepository(db),
        chunk_repository=DocumentChunkRepository(db),
        embedding_service=embedding_service,
    )


def get_rag_service(db: Session = Depends(get_db)) -> AutoModelRagService:
    asset_repository = AssetRepository(db)
    embedding_service = EmbeddingService(asset_repository=asset_repository)
    search_service = SemanticSearchService(
        project_repository=ProjectRepository(db),
        chunk_repository=DocumentChunkRepository(db),
        embedding_service=embedding_service,
    )
    return AutoModelRagService(
        search_service=search_service,
        asset_repository=asset_repository,
        conversation_repository=ConversationRepository(db),
        benchmark_repository=BenchmarkRepository(db),
    )


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


@project_search_router.post("/search", response_model=SemanticSearchResponse)
def semantic_search(
    project_id: UUID,
    data: SemanticSearchRequest,
    service: SemanticSearchService = Depends(get_search_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> SemanticSearchResponse:
    return service.search(project_id, data)


@project_search_router.post("/ask", response_model=RagAnswerResponse)
def ask_project(
    project_id: UUID,
    data: RagAnswerRequest,
    service: AutoModelRagService = Depends(get_rag_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> RagAnswerResponse:
    return service.answer(project_id, user.id, data)


@project_search_router.post("/ask/stream")
def stream_project_answer(
    project_id: UUID,
    data: RagAnswerRequest,
    service: AutoModelRagService = Depends(get_rag_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> StreamingResponse:
    events = service.stream_answer(project_id, user.id, data)

    def encode_events():
        try:
            for event in events:
                yield (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
        finally:
            close = getattr(events, "close", None)
            if callable(close):
                close()

    return StreamingResponse(
        encode_events(),
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
