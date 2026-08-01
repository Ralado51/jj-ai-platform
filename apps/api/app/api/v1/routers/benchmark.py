from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse
from app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


def get_service(db: Session = Depends(get_db)) -> BenchmarkService:
    return BenchmarkService(BenchmarkRepository(db))


@router.post("/run", response_model=BenchmarkRunResponse)
def run_benchmark(
    payload: BenchmarkRunRequest,
    service: BenchmarkService = Depends(get_service),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> BenchmarkRunResponse:
    try:
        return service.run(payload, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
