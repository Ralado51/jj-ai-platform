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
    def stream_generate(self, *, system_prompt: str, user_prompt: str) -> Iterator[str]:
        raise NotImplementedError


class OllamaChatProvider(ChatProvider):
    name = "ollama"

    def __init__(self, *, base_url: str, model: str, timeout_seconds: float, temperature: float, max_tokens: int = 2048, repeat_penalty: float = 1.12, max_characters: int = 24000) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.repeat_penalty = repeat_penalty
        self.max_characters = max_characters
        self.last_usage: dict[str, int] = {}

    def _payload(self, *, system_prompt: str, user_prompt: str, stream: bool) -> dict:
        return {
            "model": self.model,
            "stream": stream,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "repeat_penalty": self.repeat_penalty,
            },
        }

    def _capture_usage(self, payload: dict) -> None:
        self.last_usage = {
            "prompt_tokens": int(payload.get("prompt_eval_count") or 0),
            "completion_tokens": int(payload.get("eval_count") or 0),
        }

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.last_usage = {}
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=self._payload(system_prompt=system_prompt, user_prompt=user_prompt, stream=False),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        self._capture_usage(payload)
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ChatProviderError("Invalid Ollama chat response")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ChatProviderError("Ollama returned an empty answer")
        return content[: self.max_characters].strip()

    def stream_generate(self, *, system_prompt: str, user_prompt: str) -> Iterator[str]:
        self.last_usage = {}
        received_content = False
        generated_characters = 0
        recent_chunks: list[str] = []

        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=self._payload(system_prompt=system_prompt, user_prompt=user_prompt, stream=True),
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
                        normalized = " ".join(content.split())
                        recent_chunks.append(normalized)
                        recent_chunks = recent_chunks[-12:]
                        if normalized and recent_chunks.count(normalized) >= 8:
                            break
                        remaining = self.max_characters - generated_characters
                        if remaining <= 0:
                            break
                        chunk = content[:remaining]
                        generated_characters += len(chunk)
                        received_content = True
                        yield chunk
                        if generated_characters >= self.max_characters:
                            break
                if payload.get("done") is True:
                    self._capture_usage(payload)
                    break
        if not received_content:
            raise ChatProviderError("Ollama returned an empty streamed answer")
