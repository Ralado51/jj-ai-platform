from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.api.v1.routers.agents import get_service as get_agent_service
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.playground_repository import PlaygroundRepository
from app.schemas.playground import (
    PlaygroundRunCreate,
    PlaygroundRunResponse,
    PlaygroundSessionCreate,
    PlaygroundSessionResponse,
)
from app.services.agent_service import AgentService
from app.services.playground_service import PlaygroundService

router = APIRouter(prefix="/playground", tags=["playground"])


def get_service(
    db: Session = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
) -> PlaygroundService:
    return PlaygroundService(
        PlaygroundRepository(db), agent_service=agent_service
    )


@router.post(
    "/sessions",
    response_model=PlaygroundSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: PlaygroundSessionCreate,
    service: PlaygroundService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PlaygroundSessionResponse:
    return service.create_session(
        owner_id=user.id, project_id=payload.project_id, name=payload.name
    )


@router.get("/sessions", response_model=list[PlaygroundSessionResponse])
def list_sessions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: PlaygroundService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[PlaygroundSessionResponse]:
    return service.repository.list_sessions(
        owner_id=user.id, offset=offset, limit=limit
    )


@router.post(
    "/sessions/{session_id}/runs",
    response_model=PlaygroundRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_experiment(
    session_id: UUID,
    payload: PlaygroundRunCreate,
    service: PlaygroundService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PlaygroundRunResponse:
    session = service.get_session(session_id=session_id, owner_id=user.id)
    return service.run(session=session, payload=payload, owner_id=user.id)


@router.get(
    "/sessions/{session_id}/runs",
    response_model=list[PlaygroundRunResponse],
)
def list_runs(
    session_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: PlaygroundService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[PlaygroundRunResponse]:
    service.get_session(session_id=session_id, owner_id=user.id)
    return service.repository.list_runs(
        session_id=session_id,
        owner_id=user.id,
        offset=offset,
        limit=limit,
    )
