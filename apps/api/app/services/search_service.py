from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from app.services.embedding_providers import EmbeddingProviderError
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SemanticSearchService:
    def __init__(
        self,
        *,
        project_repository: ProjectRepository,
        chunk_repository: DocumentChunkRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        self.project_repository = project_repository
        self.chunk_repository = chunk_repository
        self.embedding_service = embedding_service

    def search(
        self,
        project_id: UUID,
        data: SemanticSearchRequest,
    ) -> SemanticSearchResponse:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado.",
            )

        try:
            provider = self.embedding_service.get_provider()
            query_embedding = provider.create_embeddings([data.query])[0]
        except EmbeddingProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A integração de embeddings não está configurada corretamente.",
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to generate query embedding for project %s using provider %s",
                project_id,
                getattr(provider, "name", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível gerar o embedding da consulta.",
            ) from exc

        matches = self.chunk_repository.semantic_search(
            project_id=project_id,
            query_embedding=query_embedding,
            limit=data.top_k,
        )
        results = [
            SemanticSearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                project_id=chunk.project_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=round(score, 6),
            )
            for chunk, score in matches
            if score >= data.min_score
        ]

        return SemanticSearchResponse(
            project_id=project_id,
            query=data.query,
            provider=provider.name,
            model=provider.model,
            total=len(results),
            results=results,
        )
