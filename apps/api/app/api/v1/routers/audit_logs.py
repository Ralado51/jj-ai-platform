from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_logs import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def get_repository(db: Session = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    project_id: UUID | None = None,
    event_name: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    occurred_from: dt.datetime | None = None,
    occurred_to: dt.datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    repository: AuditLogRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> AuditLogListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    items, total = repository.list(
        actor_id=None if user.role == UserRole.ADMIN else user.id,
        project_id=project_id,
        event_name=event_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        offset=(safe_page - 1) * safe_page_size,
        limit=safe_page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )
