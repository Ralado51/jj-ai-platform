from hashlib import sha256

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
)
from app.services.email_service import EmailService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)
        self.email_service = EmailService()

    def register(self, payload: UserCreate) -> User:
        if self.repository.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            role=UserRole.MEMBER,
        )
        return self.repository.create(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.repository.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        token = create_access_token(str(user.id), user.role.value)
        return TokenResponse(access_token=token, user=user)

    def forgot_password(self, payload: ForgotPasswordRequest) -> None:
        user = self.repository.get_by_email(payload.email)
        if not user or not user.is_active:
            return

        token = create_password_reset_token(str(user.id), user.hashed_password)
        self.email_service.send_password_reset(user.email, token)

    def reset_password(self, payload: ResetPasswordRequest) -> None:
        try:
            token_data = decode_password_reset_token(payload.token)
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            ) from exc

        user = self.repository.get_by_id(token_data.get("sub", ""))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        current_fingerprint = sha256(user.hashed_password.encode()).hexdigest()
        if token_data.get("pwd") != current_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        self.repository.update_password(user, hash_password(payload.password))
