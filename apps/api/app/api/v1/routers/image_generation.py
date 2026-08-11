from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_roles
from app.core.config import get_settings
from app.models.user import User, UserRole
from app.schemas.image_generation import (
    BatchImageGenerationRequest,
    BatchImageGenerationResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from app.services.image_generation_provider import ImageGenerationError
from app.services.image_generation_service import ImageGenerationService

router = APIRouter(prefix="/images", tags=["image-generation"])


def get_service() -> ImageGenerationService:
    return ImageGenerationService(get_settings())


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    payload: ImageGenerationRequest,
    service: ImageGenerationService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ImageGenerationResponse:
    try:
        return await service.generate(payload)
    except ImageGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/generate/batch", response_model=BatchImageGenerationResponse)
async def generate_images_batch(
    payload: BatchImageGenerationRequest,
    service: ImageGenerationService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> BatchImageGenerationResponse:
    return await service.generate_batch(payload)
