from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.agent_repository import AgentRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.agents import (
    AgentDescriptorResponse,
    AgentExecutionResponse,
    AgentMemoryResponse,
    AgentOrchestrationRequest,
    AgentOrchestrationResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator
from app.services.agent_service import AgentService
from app.services.auto_model_rag_service import AutoModelRagService
from app.services.chat_providers import ChatProviderError
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SemanticSearchService

router = APIRouter(prefix="/agents", tags=["agents"])


def get_service(db: Session = Depends(get_db)) -> AgentService:
    asset_repository = AssetRepository(db)
    benchmark_repository = BenchmarkRepository(db)
    search_service = SemanticSearchService(
        project_repository=ProjectRepository(db),
        chunk_repository=DocumentChunkRepository(db),
        embedding_service=EmbeddingService(asset_repository=asset_repository),
    )
    rag_service = AutoModelRagService(
        search_service=search_service,
        asset_repository=asset_repository,
        conversation_repository=ConversationRepository(db),
        benchmark_repository=benchmark_repository,
    )
    return AgentService(
        repository=AgentRepository(db),
        benchmark_repository=benchmark_repository,
        rag_service=rag_service,
    )


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
            project_id=payload.project_id,
            session_key=payload.session_key,
            use_memory=payload.use_memory,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ChatProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível executar o agente no modelo local.",
        ) from exc


@router.post("/orchestrate", response_model=AgentOrchestrationResponse)
def orchestrate_agents(
    payload: AgentOrchestrationRequest,
    service: AgentService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> AgentOrchestrationResponse:
    try:
        result = AgentOrchestrator(service).run(
            initial_instruction=payload.instruction,
            steps=[
                AgentOrchestrationStep(
                    agent_id=step.agent_id,
                    instruction=step.instruction,
                )
                for step in payload.steps
            ],
            user_id=user.id,
            project_id=payload.project_id,
            session_key=payload.session_key,
            use_memory=payload.use_memory,
        )
        return AgentOrchestrationResponse(
            steps=result.steps,
            final_content=result.final_content,
            total_duration_ms=result.total_duration_ms,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ChatProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível concluir a orquestração de agentes.",
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
