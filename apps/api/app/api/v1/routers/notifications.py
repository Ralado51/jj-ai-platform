from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notifications import NotificationListResponse, NotificationMarkAllReadResponse, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_repository(db: Session = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
    repository: NotificationRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationListResponse:
    safe_limit = max(1, min(limit, 500))
    return NotificationListResponse(
        items=repository.list(user_id=user.id, unread_only=unread_only, limit=safe_limit),
        unread_count=repository.unread_count(user_id=user.id),
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    repository: NotificationRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationResponse:
    item = repository.mark_read(user_id=user.id, notification_id=notification_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return NotificationResponse.model_validate(item)


@router.post("/read-all", response_model=NotificationMarkAllReadResponse)
def mark_all_notifications_read(
    repository: NotificationRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationMarkAllReadResponse:
    return NotificationMarkAllReadResponse(updated=repository.mark_all_read(user_id=user.id))
