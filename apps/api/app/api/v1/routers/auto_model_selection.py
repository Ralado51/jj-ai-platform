from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import get_settings
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.auto_model_selection import AutoModelSelectionResponse
from app.services.auto_model_selector import AutoModelSelector
from app.services.model_router import AITaskType, ModelRouter

router = APIRouter(prefix="/model-selection", tags=["model-selection"])


def get_selector(db: Session = Depends(get_db)) -> AutoModelSelector:
    settings = get_settings()
    router_service = ModelRouter(
        default_model=settings.ollama_chat_model,
        content_model=settings.ollama_content_model,
        rag_model=settings.ollama_rag_model,
        coding_model=settings.ollama_coding_model,
        summarization_model=settings.ollama_summarization_model,
        general_model=settings.ollama_general_model,
    )
    return AutoModelSelector(
        repository=BenchmarkRepository(db),
        router=router_service,
        minimum_samples=settings.auto_model_minimum_samples,
        minimum_average_score=settings.auto_model_minimum_average_score,
    )


@router.get("/recommendation", response_model=AutoModelSelectionResponse)
def get_model_recommendation(
    task: AITaskType = Query(default=AITaskType.GENERAL),
    selector: AutoModelSelector = Depends(get_selector),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> AutoModelSelectionResponse:
    selection = selector.select(user_id=user.id, task=task)
    return AutoModelSelectionResponse(
        task=selection.task,
        model=selection.model,
        reason=selection.reason,
        source=selection.source,
        sample_size=selection.sample_size,
        average_score=selection.average_score,
        average_duration_ms=selection.average_duration_ms,
        used_fallback=selection.used_fallback,
    )
