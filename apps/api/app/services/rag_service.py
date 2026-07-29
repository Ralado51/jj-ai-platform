from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.search import (
    RagAnswerRequest,
    RagAnswerResponse,
    RagSource,
    SemanticSearchRequest,
)
from app.services.chat_providers import ChatProviderError, OllamaChatProvider
from app.services.search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self, *, search_service: SemanticSearchService) -> None:
        self.search_service = search_service
        self.settings = get_settings()

    def answer(self, project_id: UUID, data: RagAnswerRequest) -> RagAnswerResponse:
        search_response = self.search_service.search(
            project_id,
            SemanticSearchRequest(
                query=data.question,
                top_k=data.top_k,
                min_score=data.min_score,
            ),
        )
        if not search_response.results:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nenhum trecho relevante foi encontrado para responder à pergunta.",
            )

        provider = OllamaChatProvider(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_chat_model,
            timeout_seconds=self.settings.ollama_chat_timeout_seconds,
            temperature=self.settings.ollama_chat_temperature,
        )
        context = "\n\n".join(
            (
                f"[Fonte {index}] documento={result.document_id} "
                f"chunk={result.chunk_index} score={result.score}\n{result.content}"
            )
            for index, result in enumerate(search_response.results, start=1)
        )
        system_prompt = (
            "Você é um assistente de RAG da JJ AI Platform. "
            "Responda em português do Brasil usando somente o contexto fornecido. "
            "Não use conhecimento externo e não invente informações. "
            "Quando a resposta não estiver no contexto, diga claramente que não há "
            "informação suficiente. Cite as fontes usadas no formato [Fonte N]. "
            "Seja objetivo e preserve fatos, nomes e números do contexto."
        )
        user_prompt = (
            f"CONTEXTO\n{context}\n\n"
            f"PERGUNTA\n{data.question}\n\n"
            "Produza uma resposta direta e fundamentada nas fontes acima."
        )

        try:
            answer = provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except (httpx.HTTPError, ChatProviderError) as exc:
            logger.exception(
                "Failed to generate RAG answer for project %s using model %s",
                project_id,
                provider.model,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível gerar a resposta com o modelo local.",
            ) from exc

        return RagAnswerResponse(
            project_id=project_id,
            question=data.question,
            answer=answer,
            chat_provider=provider.name,
            chat_model=provider.model,
            embedding_provider=search_response.provider,
            embedding_model=search_response.model,
            sources=[
                RagSource(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    chunk_index=result.chunk_index,
                    score=result.score,
                )
                for result in search_response.results
            ],
        )
