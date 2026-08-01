from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_roles
from app.models.user import User, UserRole
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse
from app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


def get_service() -> BenchmarkService:
    return BenchmarkService()


@router.post("/run", response_model=BenchmarkRunResponse)
def run_benchmark(
    payload: BenchmarkRunRequest,
    service: BenchmarkService = Depends(get_service),
    _: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)
    ),
) -> BenchmarkRunResponse:
    try:
        return service.run(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
