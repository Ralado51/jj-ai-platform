from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.repositories.asset_repository import AssetRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.schemas.document import DocumentEmbeddingResponse
from app.services.embedding_providers import (
    EmbeddingProvider,
    EmbeddingProviderError,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        asset_repository: AssetRepository,
        chunk_repository: DocumentChunkRepository | None = None,
    ) -> None:
        self.asset_repository = asset_repository
        self.chunk_repository = chunk_repository or DocumentChunkRepository(asset_repository.db)
        self.settings = get_settings()

    def embed_document(self, document_id: UUID) -> DocumentEmbeddingResponse:
        document = self.asset_repository.get_document(document_id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado.",
            )

        chunks = self.chunk_repository.list_for_document(document_id)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O documento precisa ser processado antes da geração de embeddings.",
            )

        try:
            provider = self._get_provider()
        except EmbeddingProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A integração de embeddings não está configurada corretamente.",
            ) from exc

        metadata = dict(document.asset_metadata or {})
        metadata["embedding_status"] = "processing"
        metadata["embedding_provider"] = provider.name
        metadata.pop("embedding_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        try:
            embeddings = provider.create_embeddings([chunk.content for chunk in chunks])
            self.chunk_repository.update_embeddings(chunks=chunks, embeddings=embeddings)
        except (httpx.HTTPError, EmbeddingProviderError, ValueError, SQLAlchemyError) as exc:
            self.asset_repository.db.rollback()
            logger.exception(
                "Failed to generate embeddings for document %s using provider %s",
                document_id,
                provider.name,
            )
            metadata = dict(document.asset_metadata or {})
            metadata["embedding_status"] = "failed"
            metadata["embedding_error"] = str(exc)
            document.asset_metadata = metadata
            self.asset_repository.save(document)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível gerar os embeddings deste documento.",
            ) from exc

        metadata = dict(document.asset_metadata or {})
        metadata.update(
            {
                "embedding_status": "completed",
                "embedding_provider": provider.name,
                "embedding_model": provider.model,
                "embedding_dimensions": provider.dimensions,
                "embedded_chunk_count": len(chunks),
            }
        )
        metadata.pop("embedding_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        return DocumentEmbeddingResponse(
            document_id=document.id,
            status="completed",
            provider=provider.name,
            model=provider.model,
            dimensions=provider.dimensions,
            embedded_chunk_count=len(chunks),
            message="Embeddings gerados e armazenados com sucesso.",
        )

    def _get_provider(self) -> EmbeddingProvider:
        provider_name = self.settings.embedding_provider.strip().lower()
        if provider_name == "ollama":
            return OllamaEmbeddingProvider(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_embedding_model,
                dimensions=self.settings.ollama_embedding_dimensions,
                timeout_seconds=self.settings.ollama_timeout_seconds,
            )
        if provider_name == "openai":
            return OpenAIEmbeddingProvider(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.openai_embedding_dimensions,
                timeout_seconds=self.settings.openai_timeout_seconds,
            )
        raise EmbeddingProviderError(
            f"Unsupported embedding provider: {self.settings.embedding_provider}"
        )
