import asyncio

from app.core.config import Settings
from app.schemas.image_generation import (
    BatchImageGenerationItem,
    BatchImageGenerationRequest,
    ImageGenerationRequest,
)
from app.services.image_generation_provider import GeneratedImage, ImageGenerationError
from app.services.image_generation_service import ImageGenerationService


class FakeProvider:
    async def generate(self, *, prompt, model, width, height, seed):
        if prompt == "fail":
            raise ImageGenerationError("provider failed")
        return GeneratedImage(
            provider="huggingface",
            model=model or "fake-model",
            mime_type="image/png",
            image_base64="aW1hZ2U=",
            seed=seed,
            latency_ms=12,
        )


def test_generate_returns_provider_result():
    service = ImageGenerationService(Settings())
    service.providers["huggingface"] = FakeProvider()

    result = asyncio.run(
        service.generate(
            ImageGenerationRequest(
                provider="huggingface",
                prompt="hero",
                seed=42,
            )
        )
    )

    assert result.model == "fake-model"
    assert result.image_base64 == "aW1hZ2U="
    assert result.seed == 42


def test_batch_keeps_partial_failures():
    service = ImageGenerationService(Settings(image_generation_batch_concurrency=2))
    service.providers["huggingface"] = FakeProvider()

    result = asyncio.run(
        service.generate_batch(
            BatchImageGenerationRequest(
                provider="huggingface",
                items=[
                    BatchImageGenerationItem(id="ok", prompt="hero"),
                    BatchImageGenerationItem(id="bad", prompt="fail"),
                ],
            )
        )
    )

    assert result.total == 2
    assert result.completed == 1
    assert result.failed == 1
    assert result.results[0].status == "completed"
    assert result.results[1].status == "failed"
    assert result.results[1].error == "provider failed"
