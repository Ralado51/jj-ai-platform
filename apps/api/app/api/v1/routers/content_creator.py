from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_roles
from app.models.user import User, UserRole
from app.schemas.content_creator import ContentCreatorBriefing, ContentCreatorResponse
from app.services.content_creator_service import ContentCreatorService

router = APIRouter(
    prefix="/projects/{project_id}/apps/content-creator",
    tags=["content-creator"],
)


def get_service() -> ContentCreatorService:
    return ContentCreatorService()


@router.post("/generate", response_model=ContentCreatorResponse)
def generate_content(
    project_id: UUID,
    payload: ContentCreatorBriefing,
    service: ContentCreatorService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> ContentCreatorResponse:
    del project_id
    return service.generate(payload)
