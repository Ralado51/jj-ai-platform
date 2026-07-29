from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider cannot return valid vectors."""


class EmbeddingProvider(ABC):
    name: str
    model: str
    dimensions: int

    @abstractmethod
    def create_embeddings(self, inputs: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def _validate(self, inputs: list[str], embeddings: list[list[float]]) -> list[list[float]]:
        if len(embeddings) != len(inputs):
            raise EmbeddingProviderError(
                "Embedding response count does not match input count"
            )
        if any(len(embedding) != self.dimensions for embedding in embeddings):
            raise EmbeddingProviderError(
                f"Embedding dimensions do not match configured size {self.dimensions}"
            )
        return embeddings


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def create_embeddings(self, inputs: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": inputs},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings", [])
        if not isinstance(embeddings, list):
            raise EmbeddingProviderError("Invalid Ollama embedding response")
        return self._validate(inputs, embeddings)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        if not api_key:
            raise EmbeddingProviderError("OPENAI_API_KEY is not configured")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def create_embeddings(self, inputs: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": inputs,
                "dimensions": self.dimensions,
                "encoding_format": "float",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = sorted(payload.get("data", []), key=lambda item: item["index"])
        embeddings = [item["embedding"] for item in data]
        return self._validate(inputs, embeddings)
