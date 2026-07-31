from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from time import perf_counter
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.repositories.asset_repository import AssetRepository
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.search import (
    RagAnswerRequest,
    RagAnswerResponse,
    RagExecutionMetrics,
    RagSource,
    SemanticSearchRequest,
)
from app.services.chat_providers import ChatProviderError, OllamaChatProvider
from app.services.prompt_engine import PromptEngine
from app.services.search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        *,
        search_service: SemanticSearchService,
        asset_repository: AssetRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self.search_service = search_service
        self.asset_repository = asset_repository
        self.conversation_repository = conversation_repository
        self.settings = get_settings()
        self.prompt_engine = PromptEngine()

    def answer(
        self,
        project_id: UUID,
        user_id: UUID,
        data: RagAnswerRequest,
    ) -> RagAnswerResponse:
        total_started_at = perf_counter()
        prepared = self._prepare_answer(project_id, user_id, data)
        provider = prepared["provider"]
        selected_results = prepared["selected_results"]

        generation_started_at = perf_counter()
        try:
            answer = provider.generate(
                system_prompt=prepared["system_prompt"],
                user_prompt=prepared["user_prompt"],
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

        generation_time_ms = self._elapsed_ms(generation_started_at)
        answer = self._normalize_inline_citations(answer, len(selected_results))
        metrics = self._build_metrics(
            selected_results=selected_results,
            context=prepared["context"],
            search_time_ms=prepared["search_time_ms"],
            generation_time_ms=generation_time_ms,
            total_started_at=total_started_at,
        )

        return RagAnswerResponse(
            project_id=project_id,
            question=data.question,
            answer=answer,
            chat_provider=provider.name,
            chat_model=provider.model,
            embedding_provider=prepared["search_response"].provider,
            embedding_model=prepared["search_response"].model,
            metrics=metrics,
            sources=prepared["sources"],
        )

    def stream_answer(
        self,
        project_id: UUID,
        user_id: UUID,
        data: RagAnswerRequest,
    ) -> Iterator[dict]:
        total_started_at = perf_counter()
        prepared = self._prepare_answer(project_id, user_id, data)
        provider = prepared["provider"]
        selected_results = prepared["selected_results"]

        metadata = {
            "type": "metadata",
            "project_id": str(project_id),
            "question": data.question,
            "chat_provider": provider.name,
            "chat_model": provider.model,
            "embedding_provider": prepared["search_response"].provider,
            "embedding_model": prepared["search_response"].model,
            "sources": [source.model_dump(mode="json") for source in prepared["sources"]],
        }

        def event_stream() -> Iterator[dict]:
            yield metadata
            generation_started_at = perf_counter()
            answer_parts: list[str] = []

            try:
                for token in provider.stream_generate(
                    system_prompt=prepared["system_prompt"],
                    user_prompt=prepared["user_prompt"],
                ):
                    answer_parts.append(token)
                    yield {"type": "token", "content": token}
            except (httpx.HTTPError, ChatProviderError) as exc:
                logger.exception(
                    "Failed to stream RAG answer for project %s using model %s",
                    project_id,
                    provider.model,
                )
                yield {
                    "type": "error",
                    "detail": "Não foi possível gerar a resposta com o modelo local.",
                }
                return

            generation_time_ms = self._elapsed_ms(generation_started_at)
            answer = self._normalize_inline_citations(
                "".join(answer_parts),
                len(selected_results),
            )
            metrics = self._build_metrics(
                selected_results=selected_results,
                context=prepared["context"],
                search_time_ms=prepared["search_time_ms"],
                generation_time_ms=generation_time_ms,
                total_started_at=total_started_at,
            )
            yield {
                "type": "done",
                "answer": answer,
                "metrics": metrics.model_dump(mode="json"),
            }

        return event_stream()

    def _prepare_answer(
        self,
        project_id: UUID,
        user_id: UUID,
        data: RagAnswerRequest,
    ) -> dict:
        retrieval_limit = max(data.top_k, self.settings.rag_retrieval_top_k)
        search_started_at = perf_counter()
        search_response = self.search_service.search(
            project_id,
            SemanticSearchRequest(
                query=data.question,
                top_k=retrieval_limit,
                min_score=data.min_score,
            ),
        )
        search_time_ms = self._elapsed_ms(search_started_at)

        if not search_response.results:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nenhum trecho relevante foi encontrado para responder à pergunta.",
            )

        selected_results, context = self._build_context(search_response.results)
        if not selected_results:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Os trechos encontrados excederam o limite de contexto disponível.",
            )

        conversation_history = self._load_conversation_history(
            project_id=project_id,
            user_id=user_id,
            conversation_id=data.conversation_id,
        )

        provider = OllamaChatProvider(
            base_url=self.settings.ollama_base_url,
            model=self.settings.ollama_chat_model,
            timeout_seconds=self.settings.ollama_chat_timeout_seconds,
            temperature=self.settings.ollama_chat_temperature,
        )
        prompt = self.prompt_engine.build_rag_prompt(
            context=context,
            question=data.question,
            conversation_history=conversation_history,
        )
        document_names = self.asset_repository.get_document_names(
            list({result.document_id for result in selected_results})
        )
        sources = [
            RagSource(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_name=document_names.get(
                    result.document_id,
                    "Documento sem nome",
                ),
                chunk_index=result.chunk_index,
                score=result.score,
                snippet=self._build_snippet(result.content),
            )
            for result in selected_results
        ]

        return {
            "provider": provider,
            "selected_results": selected_results,
            "context": context,
            "search_response": search_response,
            "search_time_ms": search_time_ms,
            "system_prompt": prompt.system_prompt,
            "user_prompt": prompt.user_prompt,
            "sources": sources,
        }

    def _load_conversation_history(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
    ) -> str:
        if conversation_id is None:
            return ""

        conversation = self.conversation_repository.get_for_project(
            conversation_id=conversation_id,
            project_id=project_id,
            user_id=user_id,
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa não encontrada neste projeto.",
            )

        messages = conversation.messages[-12:]
        return "\n".join(
            f"{self._role_label(message.role)}: {message.content.strip()}"
            for message in messages
            if message.content.strip()
        )

    @staticmethod
    def _role_label(role: str) -> str:
        return "Usuário" if role == "user" else "Assistente"

    def _build_metrics(
        self,
        *,
        selected_results: list,
        context: str,
        search_time_ms: int,
        generation_time_ms: int,
        total_started_at: float,
    ) -> RagExecutionMetrics:
        return RagExecutionMetrics(
            confidence=self._calculate_confidence(selected_results),
            retrieved_chunks=len(selected_results),
            context_size=len(context),
            search_time_ms=search_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=self._elapsed_ms(total_started_at),
        )

    def _build_context(self, results: list) -> tuple[list, str]:
        selected_results = []
        context_parts: list[str] = []
        used_characters = 0
        max_characters = self.settings.rag_max_context_characters

        for result in results:
            source_number = len(selected_results) + 1
            header = (
                f"[Fonte {source_number}] documento={result.document_id} "
                f"chunk={result.chunk_index} score={result.score}\n"
            )
            separator_size = 2 if context_parts else 0
            remaining = max_characters - used_characters - separator_size - len(header)
            if remaining <= 0:
                break

            content = result.content.strip()
            if len(content) > remaining:
                content = content[:remaining].rstrip()
            if not content:
                break

            part = f"{header}{content}"
            context_parts.append(part)
            selected_results.append(result)
            used_characters += separator_size + len(part)

            if used_characters >= max_characters:
                break

        return selected_results, "\n\n".join(context_parts)

    @staticmethod
    def _build_snippet(content: str, max_characters: int = 280) -> str:
        compact = " ".join(content.split())
        if len(compact) <= max_characters:
            return compact
        return f"{compact[: max_characters - 1].rstrip()}…"

    @staticmethod
    def _normalize_inline_citations(answer: str, source_count: int) -> str:
        cleaned = answer.strip()
        if not cleaned or cleaned.startswith("Não encontrei essa informação"):
            return cleaned

        lines = [line.strip() for line in cleaned.splitlines()]
        normalized_lines: list[str] = []
        citation_only = re.compile(r"^(?:\[Fonte\s+\d+\]\s*)+$", re.IGNORECASE)

        for line in lines:
            if not line:
                if normalized_lines and normalized_lines[-1] != "":
                    normalized_lines.append("")
                continue

            if citation_only.fullmatch(line) and normalized_lines:
                previous_index = len(normalized_lines) - 1
                while previous_index >= 0 and not normalized_lines[previous_index]:
                    previous_index -= 1
                if previous_index >= 0:
                    normalized_lines[previous_index] = (
                        f"{normalized_lines[previous_index].rstrip()} {line}"
                    )
                    continue

            normalized_lines.append(line)

        normalized = "\n".join(normalized_lines).strip()
        citations = [
            int(value)
            for value in re.findall(
                r"\[Fonte\s+(\d+)\]",
                normalized,
                flags=re.IGNORECASE,
            )
        ]
        valid_citations = [value for value in citations if 1 <= value <= source_count]
        if valid_citations:
            return normalized

        return f"{normalized.rstrip()} [Fonte 1]"

    @staticmethod
    def _calculate_confidence(results: list) -> float:
        if not results:
            return 0.0
        scores = [max(0.0, min(1.0, float(result.score))) for result in results]
        weighted_score = sum(
            score * (1 / index) for index, score in enumerate(scores, start=1)
        )
        weight_total = sum(1 / index for index in range(1, len(scores) + 1))
        return round(weighted_score / weight_total, 6)

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, round((perf_counter() - started_at) * 1000))
