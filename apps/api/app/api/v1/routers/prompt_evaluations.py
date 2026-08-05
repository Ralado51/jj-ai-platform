from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.api.v1.routers.prompt_templates import get_service as get_prompt_service
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.prompt_evaluation_repository import PromptEvaluationRepository
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.schemas.prompt_evaluations import PromptEvaluationCreate, PromptEvaluationResponse
from app.services.prompt_evaluation_service import PromptEvaluationService
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter(prefix="/prompt-templates", tags=["prompt-evaluations"])


def get_service(db: Session = Depends(get_db)) -> PromptEvaluationService:
    return PromptEvaluationService(
        PromptEvaluationRepository(db),
        ResourceVersionRepository(db),
    )


@router.post("/{prompt_id}/evaluations", response_model=PromptEvaluationResponse)
def run_prompt_evaluation(
    prompt_id: UUID,
    payload: PromptEvaluationCreate,
    prompt_service: PromptTemplateService = Depends(get_prompt_service),
    service: PromptEvaluationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PromptEvaluationResponse:
    template = prompt_service.get(prompt_id, user)
    return service.run(template=template, payload=payload, user=user)


@router.get("/{prompt_id}/evaluations", response_model=list[PromptEvaluationResponse])
def list_prompt_evaluations(
    prompt_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    prompt_service: PromptTemplateService = Depends(get_prompt_service),
    service: PromptEvaluationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[PromptEvaluationResponse]:
    template = prompt_service.get(prompt_id, user)
    items, _ = service.list(template=template, user=user, offset=offset, limit=limit)
    return items
