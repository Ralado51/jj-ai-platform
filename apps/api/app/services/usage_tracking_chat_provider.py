from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from uuid import UUID

from app.repositories.ai_usage_repository import AIUsageRepository
from app.services.ai_usage_service import AIUsageService, UsageMeasurement
from app.services.chat_providers import ChatProvider


class UsageTrackingChatProvider(ChatProvider):
    def __init__(
        self,
        *,
        provider: ChatProvider,
        repository: AIUsageRepository,
        user_id: UUID,
        project_id: UUID | None = None,
        workflow_execution_id: UUID | None = None,
        workflow_step: int | None = None,
        agent_id: UUID | None = None,
        task: str | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.user_id = user_id
        self.project_id = project_id
        self.workflow_execution_id = workflow_execution_id
        self.workflow_step = workflow_step
        self.agent_id = agent_id
        self.task = task
        self.name = provider.name
        self.model = provider.model

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4) if text else 0

    def _record(self, *, system_prompt: str, user_prompt: str, content: str, started_at: dt.datetime, finished_at: dt.datetime) -> None:
        usage = getattr(self.provider, "last_usage", None) or {}
        prompt_tokens = int(usage.get("prompt_tokens") or self._estimate_tokens(system_prompt + user_prompt))
        completion_tokens = int(usage.get("completion_tokens") or self._estimate_tokens(content))
        AIUsageService(self.repository).record(
            UsageMeasurement(
                user_id=self.user_id,
                project_id=self.project_id,
                workflow_execution_id=self.workflow_execution_id,
                workflow_step=self.workflow_step,
                agent_id=self.agent_id,
                provider=self.name,
                model=self.model,
                task=self.task,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
                started_at=started_at,
                finished_at=finished_at,
            )
        )

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        started_at = dt.datetime.now(dt.UTC)
        content = self.provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        finished_at = dt.datetime.now(dt.UTC)
        self._record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            content=content,
            started_at=started_at,
            finished_at=finished_at,
        )
        return content

    def stream_generate(self, *, system_prompt: str, user_prompt: str) -> Iterator[str]:
        started_at = dt.datetime.now(dt.UTC)
        chunks: list[str] = []
        for chunk in self.provider.stream_generate(system_prompt=system_prompt, user_prompt=user_prompt):
            chunks.append(chunk)
            yield chunk
        finished_at = dt.datetime.now(dt.UTC)
        self._record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            content="".join(chunks),
            started_at=started_at,
            finished_at=finished_at,
        )
