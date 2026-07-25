from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    service: AuthService = Depends(get_service),
) -> UserResponse:
    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_service),
) -> TokenResponse:
    return service.login(payload)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user
