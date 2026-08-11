from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.schemas.image_generation import (
    BatchImageGenerationRequest,
    BatchImageGenerationResponse,
    BatchImageGenerationResult,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from app.services.image_generation_provider import (
    GoogleImageProvider,
    HuggingFaceImageProvider,
    ImageGenerationError,
)


class ImageGenerationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers = {
            "huggingface": HuggingFaceImageProvider(settings),
            "google": GoogleImageProvider(settings),
        }

    async def generate(self, payload: ImageGenerationRequest) -> ImageGenerationResponse:
        provider = self.providers[payload.provider]
        result = await provider.generate(
            prompt=payload.prompt,
            model=payload.model,
            width=payload.width,
            height=payload.height,
            seed=payload.seed,
        )
        return ImageGenerationResponse(
            provider=payload.provider,
            model=result.model,
            mime_type=result.mime_type,
            image_base64=result.image_base64,
            seed=result.seed,
            latency_ms=result.latency_ms,
        )

    async def generate_batch(
        self, payload: BatchImageGenerationRequest
    ) -> BatchImageGenerationResponse:
        semaphore = asyncio.Semaphore(max(1, self.settings.image_generation_batch_concurrency))

        async def run_item(item):
            async with semaphore:
                try:
                    image = await self.generate(
                        ImageGenerationRequest(
                            provider=payload.provider,
                            model=item.model,
                            prompt=item.prompt,
                            width=item.width,
                            height=item.height,
                            seed=item.seed,
                        )
                    )
                    return BatchImageGenerationResult(
                        id=item.id,
                        status="completed",
                        image=image,
                    )
                except ImageGenerationError as exc:
                    return BatchImageGenerationResult(
                        id=item.id,
                        status="failed",
                        error=str(exc),
                    )

        results = await asyncio.gather(*(run_item(item) for item in payload.items))
        completed = sum(1 for result in results if result.status == "completed")
        return BatchImageGenerationResponse(
            provider=payload.provider,
            total=len(results),
            completed=completed,
            failed=len(results) - completed,
            results=results,
        )
