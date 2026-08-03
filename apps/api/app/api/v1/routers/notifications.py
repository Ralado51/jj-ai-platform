import math
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
    severity: str | None = None,
    type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    repository: NotificationRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    total = repository.count(
        user_id=user.id,
        unread_only=unread_only,
        severity=severity,
        type=type,
    )
    return NotificationListResponse(
        items=repository.list(
            user_id=user.id,
            unread_only=unread_only,
            severity=severity,
            type=type,
            offset=(safe_page - 1) * safe_page_size,
            limit=safe_page_size,
        ),
        unread_count=repository.unread_count(user_id=user.id),
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        total_pages=max(1, math.ceil(total / safe_page_size)),
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
