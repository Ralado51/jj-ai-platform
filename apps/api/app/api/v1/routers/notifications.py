import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.notification_preference_repository import NotificationPreferenceRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification_preferences import NotificationPreferenceResponse, NotificationPreferenceUpdate
from app.schemas.notifications import NotificationListResponse, NotificationMarkAllReadResponse, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_repository(db: Session = Depends(get_db)) -> NotificationRepository:
    return NotificationRepository(db)


def get_preference_repository(db: Session = Depends(get_db)) -> NotificationPreferenceRepository:
    return NotificationPreferenceRepository(db)


@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    repository: NotificationPreferenceRepository = Depends(get_preference_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationPreferenceResponse:
    return NotificationPreferenceResponse.model_validate(repository.get_or_create(user_id=user.id, default_email=user.email))


@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    repository: NotificationPreferenceRepository = Depends(get_preference_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> NotificationPreferenceResponse:
    email_address = str(payload.email_address) if payload.email_address else None
    if payload.email_enabled and not (email_address or user.email):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email address is required when email notifications are enabled.")
    item = repository.update(
        user_id=user.id,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
        critical_only=payload.critical_only,
        email_address=email_address or user.email,
        default_email=user.email,
    )
    return NotificationPreferenceResponse.model_validate(item)


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
    total = repository.count(user_id=user.id, unread_only=unread_only, severity=severity, type=type)
    return NotificationListResponse(
        items=repository.list(user_id=user.id, unread_only=unread_only, severity=severity, type=type, offset=(safe_page - 1) * safe_page_size, limit=safe_page_size),
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
