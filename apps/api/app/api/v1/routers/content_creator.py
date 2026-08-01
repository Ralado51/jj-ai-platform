from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.content_creator import ContentCreatorBriefing, ContentCreatorResponse
from app.services.content_creator_service import ContentCreatorService

router = APIRouter(
    prefix="/projects/{project_id}/apps/content-creator",
    tags=["content-creator"],
)


@router.post("/generate", response_model=ContentCreatorResponse)
def generate_content(
    project_id: UUID,
    payload: ContentCreatorBriefing,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> ContentCreatorResponse:
    del project_id
    service = ContentCreatorService(
        benchmark_repository=BenchmarkRepository(db),
        user_id=user.id,
    )
    return service.generate(payload)
