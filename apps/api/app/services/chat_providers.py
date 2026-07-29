from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class ChatProviderError(RuntimeError):
    """Raised when a chat provider cannot return a valid answer."""


class ChatProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class OllamaChatProvider(ChatProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        temperature: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {"temperature": self.temperature},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ChatProviderError("Invalid Ollama chat response")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ChatProviderError("Ollama returned an empty answer")
        return content.strip()
