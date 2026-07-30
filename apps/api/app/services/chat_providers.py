from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator

import httpx


class ChatProviderError(RuntimeError):
    """Raised when a chat provider cannot return a valid answer."""


class ChatProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
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

    def _payload(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        stream: bool,
    ) -> dict:
        return {
            "model": self.model,
            "stream": stream,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": self.temperature},
        }

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=self._payload(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                stream=False,
            ),
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

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        received_content = False

        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=self._payload(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                stream=True,
            ),
            timeout=self.timeout_seconds,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ChatProviderError("Invalid Ollama stream response") from exc

                if payload.get("error"):
                    raise ChatProviderError(str(payload["error"]))

                message = payload.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content:
                        received_content = True
                        yield content

                if payload.get("done") is True:
                    break

        if not received_content:
            raise ChatProviderError("Ollama returned an empty streamed answer")
