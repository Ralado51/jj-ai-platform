from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_roles
from app.models.user import User, UserRole
from app.schemas.agents import AgentDescriptorResponse, AgentRunRequest, AgentRunResponse
from app.services.agent_service import AgentService
from app.services.chat_providers import ChatProviderError

router = APIRouter(prefix="/agents", tags=["agents"])


def get_service() -> AgentService:
    return AgentService()


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
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> AgentRunResponse:
    try:
        return service.run(
            instruction=payload.instruction,
            agent_id=payload.agent_id,
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
