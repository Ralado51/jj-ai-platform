from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from io import BytesIO
from time import perf_counter

import httpx
from huggingface_hub import InferenceClient

from app.core.config import Settings


class ImageGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedImage:
    provider: str
    model: str
    mime_type: str
    image_base64: str
    seed: int | None
    latency_ms: int


class HuggingFaceImageProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(
        self,
        *,
        prompt: str,
        model: str | None,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage:
        if not self.settings.hf_token:
            raise ImageGenerationError("HF_TOKEN is not configured.")

        selected_model = model or self.settings.hf_image_model
        started = perf_counter()

        def _generate() -> bytes:
            client = InferenceClient(
                api_key=self.settings.hf_token,
                provider=self.settings.hf_image_provider,
            )
            image = client.text_to_image(
                prompt,
                model=selected_model,
                width=width,
                height=height,
                seed=seed,
            )
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()

        try:
            image_bytes = await asyncio.to_thread(_generate)
        except Exception as exc:  # provider SDK normalizes heterogeneous upstream errors
            raise ImageGenerationError(f"Hugging Face generation failed: {exc}") from exc

        latency_ms = int((perf_counter() - started) * 1000)
        return GeneratedImage(
            provider="huggingface",
            model=selected_model,
            mime_type="image/png",
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
            seed=seed,
            latency_ms=latency_ms,
        )


class GoogleImageProvider:
    INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(
        self,
        *,
        prompt: str,
        model: str | None,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage:
        if not self.settings.gemini_api_key:
            raise ImageGenerationError("GEMINI_API_KEY is not configured.")

        selected_model = model or self.settings.gemini_image_model
        aspect_ratio = _aspect_ratio(width, height)
        payload = {
            "model": selected_model,
            "input": prompt,
            "response_format": {
                "type": "image",
                "mime_type": "image/png",
                "aspect_ratio": aspect_ratio,
                "image_size": "1K",
            },
        }
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.settings.image_generation_timeout_seconds) as client:
                response = await client.post(
                    self.INTERACTIONS_URL,
                    headers={
                        "x-goog-api-key": self.settings.gemini_api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1200]
            raise ImageGenerationError(
                f"Google image generation failed ({exc.response.status_code}): {detail}"
            ) from exc
        except Exception as exc:
            raise ImageGenerationError(f"Google image generation failed: {exc}") from exc

        image_data, mime_type = _find_image_data(body)
        if not image_data:
            raise ImageGenerationError("Google response did not contain an output image.")

        latency_ms = int((perf_counter() - started) * 1000)
        return GeneratedImage(
            provider="google",
            model=selected_model,
            mime_type=mime_type or "image/png",
            image_base64=image_data,
            seed=seed,
            latency_ms=latency_ms,
        )


def _aspect_ratio(width: int, height: int) -> str:
    ratio = width / height
    options = {
        "1:1": 1.0,
        "3:2": 1.5,
        "4:3": 4 / 3,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
        "3:4": 3 / 4,
        "2:3": 2 / 3,
    }
    return min(options, key=lambda key: abs(options[key] - ratio))


def _find_image_data(value: object) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        if value.get("type") == "image" and isinstance(value.get("data"), str):
            return value["data"], value.get("mime_type") if isinstance(value.get("mime_type"), str) else None
        for child in value.values():
            image_data, mime_type = _find_image_data(child)
            if image_data:
                return image_data, mime_type
    elif isinstance(value, list):
        for child in value:
            image_data, mime_type = _find_image_data(child)
            if image_data:
                return image_data, mime_type
    return None, None
