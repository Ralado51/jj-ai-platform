from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.ai_cost_budget_repository import AICostBudgetRepository
from app.schemas.ai_cost_budget import AICostBudgetCreateRequest, AICostBudgetResponse, AICostBudgetStatusResponse, AICostBudgetUpdateRequest
from app.services.ai_cost_budget_service import AICostBudgetService

router = APIRouter(prefix="/analytics/budgets", tags=["analytics"])


@router.get("", response_model=list[AICostBudgetStatusResponse])
def list_budgets(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER))):
    repository = AICostBudgetRepository(db)
    return AICostBudgetService(repository, db).list_statuses(user_id=user.id)


@router.post("", response_model=AICostBudgetResponse, status_code=201)
def create_budget(payload: AICostBudgetCreateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER))):
    try:
        return AICostBudgetRepository(db).create(user_id=user.id, **payload.model_dump())
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A budget already exists for this scope") from exc


@router.patch("/{budget_id}", response_model=AICostBudgetResponse)
def update_budget(budget_id: UUID, payload: AICostBudgetUpdateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER))):
    repository = AICostBudgetRepository(db)
    item = repository.get(user_id=user.id, budget_id=budget_id)
    if not item:
        raise HTTPException(status_code=404, detail="Budget not found")
    values = payload.model_dump(exclude_unset=True)
    warning = values.get("warning_threshold_percent", item.warning_threshold_percent)
    critical = values.get("critical_threshold_percent", item.critical_threshold_percent)
    if warning >= critical:
        raise HTTPException(status_code=422, detail="Warning threshold must be lower than critical threshold")
    return repository.update(item=item, values=values)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER))):
    repository = AICostBudgetRepository(db)
    item = repository.get(user_id=user.id, budget_id=budget_id)
    if not item:
        raise HTTPException(status_code=404, detail="Budget not found")
    repository.delete(item=item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
