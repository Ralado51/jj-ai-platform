from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.asset_repository import AssetRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


def get_service(
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(
        asset_repository=AssetRepository(db),
        project_repository=ProjectRepository(db),
        storage=storage,
    )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> DocumentResponse:
    return service.upload(project_id, file)
