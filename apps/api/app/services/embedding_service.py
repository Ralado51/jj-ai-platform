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

        if not self.settings.openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A integração de embeddings não está configurada.",
            )

        metadata = dict(document.asset_metadata or {})
        metadata["embedding_status"] = "processing"
        metadata.pop("embedding_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        try:
            embeddings = self._create_embeddings([chunk.content for chunk in chunks])
            self.chunk_repository.update_embeddings(chunks=chunks, embeddings=embeddings)
        except (httpx.HTTPError, ValueError, SQLAlchemyError) as exc:
            self.asset_repository.db.rollback()
            logger.exception("Failed to generate embeddings for document %s", document_id)
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
                "embedding_model": self.settings.openai_embedding_model,
                "embedding_dimensions": self.settings.openai_embedding_dimensions,
                "embedded_chunk_count": len(chunks),
            }
        )
        metadata.pop("embedding_error", None)
        document.asset_metadata = metadata
        self.asset_repository.save(document)

        return DocumentEmbeddingResponse(
            document_id=document.id,
            status="completed",
            model=self.settings.openai_embedding_model,
            dimensions=self.settings.openai_embedding_dimensions,
            embedded_chunk_count=len(chunks),
            message="Embeddings gerados e armazenados com sucesso.",
        )

    def _create_embeddings(self, inputs: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/embeddings",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.openai_embedding_model,
                "input": inputs,
                "dimensions": self.settings.openai_embedding_dimensions,
                "encoding_format": "float",
            },
            timeout=self.settings.openai_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = sorted(payload.get("data", []), key=lambda item: item["index"])
        embeddings = [item["embedding"] for item in data]

        if len(embeddings) != len(inputs):
            raise ValueError("Embedding response count does not match chunk count")
        if any(len(embedding) != self.settings.openai_embedding_dimensions for embedding in embeddings):
            raise ValueError("Embedding response dimensions do not match configuration")
        return embeddings
