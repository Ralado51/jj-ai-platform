from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.agent_repository import AgentRepository
from app.schemas.agents import (
    AgentDescriptorResponse,
    AgentExecutionResponse,
    AgentMemoryResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.services.agent_service import AgentService
from app.services.chat_providers import ChatProviderError

router = APIRouter(prefix="/agents", tags=["agents"])


def get_service(db: Session = Depends(get_db)) -> AgentService:
    return AgentService(repository=AgentRepository(db))


@router.get("", response_model=list[AgentDescriptorResponse])
def list_agents(
    service: AgentService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[AgentDescriptorResponse]:
    return service.list_agents()


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    service: AgentService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> AgentRunResponse:
    try:
        return service.run(
            instruction=payload.instruction,
            agent_id=payload.agent_id,
            user_id=user.id,
            session_key=payload.session_key,
            use_memory=payload.use_memory,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChatProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível executar o agente no modelo local.",
        ) from exc


@router.get("/executions", response_model=list[AgentExecutionResponse])
def list_agent_executions(
    agent_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[AgentExecutionResponse]:
    rows = AgentRepository(db).list_executions(
        user_id=user.id,
        agent_id=agent_id,
        limit=limit,
    )
    return [AgentExecutionResponse.model_validate(row) for row in rows]


@router.get("/{agent_id}/memory/{session_key}", response_model=list[AgentMemoryResponse])
def get_agent_memory(
    agent_id: str,
    session_key: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> list[AgentMemoryResponse]:
    rows = AgentRepository(db).recent_memory(
        user_id=user.id,
        agent_id=agent_id,
        session_key=session_key,
        limit=limit,
    )
    return [AgentMemoryResponse.model_validate(row) for row in rows]


@router.delete("/{agent_id}/memory/{session_key}", status_code=status.HTTP_204_NO_CONTENT)
def clear_agent_memory(
    agent_id: str,
    session_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> Response:
    AgentRepository(db).clear_memory(
        user_id=user.id,
        agent_id=agent_id,
        session_key=session_key,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
