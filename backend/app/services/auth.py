"""Authentication service using argon2-cffi for hashing and pyjwt for signed cookies."""

from __future__ import annotations

import json
import time
from typing import Optional

import argon2
import jwt
from fastapi import Request, Response, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from app.config import get_settings

settings = get_settings()

# Argon2 password hasher
_hasher = argon2.PasswordHasher(
    time_cost=settings.argon2_time_cost or 15,
    memory_cost=settings.argon2_memory_cost or 65536,
    parallelism=settings.argon2_parallelism or 2,
    hash_len=32,
)


class AuthCredentials(BaseModel):
    """Login credentials for authentication."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_sufficient(cls, v: str) -> str:
        """Validate password minimum length."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class PublicUser(BaseModel):
    """Public-facing user representation (no sensitive fields)."""

    id: int
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    last_login: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ErrorShape(BaseModel):
    """Standardized error response shape."""

    error: str
    message: str
    path: str | None = None


def hash_password(plain_text: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _hasher.hash(plain_text)


def verify_password(plain_text: str, hashed: str) -> bool:
    """Verify a plain-text password against an Argon2 hash."""
    try:
        _hasher.verify(hashed, plain_text)
        return True
    except Exception:
        return False


def create_access_token(
    subject: int | str,
    expires_delta_seconds: Optional[int] = None,
) -> str:
    """Create a JWT access token."""
    now = int(time.time())
    to_encode = {"sub": str(subject), "iat": now}
    if expires_delta_seconds:
        to_encode["exp"] = now + expires_delta_seconds
    else:
        # Default 15 minutes
        to_encode["exp"] = now + 15 * 60
    encoded_jwt = jwt.encode(
        to_encode,
        settings.session_secret.get_secret_value(),
        algorithm="HS256",
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.session_secret.get_secret_value(),
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_current_user(request: Request) -> PublicUser:
    """Extract the current user from the JWT cookie in the request."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_access_token(token)
    user_id: int = int(payload.get("sub"))
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    # Import here to avoid circular imports
    from app.models.users import User  # type: ignore
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.config import get_db_session

    session = get_db_session()
    try:
        stmt = select(User).where(User.id == user_id)
        user = session.scalar(stmt)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return PublicUser.model_validate(user)
    finally:
        session.close()


def authenticate_user(email: str, password: str) -> Optional[PublicUser]:
    """Authenticate a user by email and password. Returns PublicUser or None."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.config import get_db_session

    session = get_db_session()
    try:
        stmt = select(User).where(User.email == email)
        user = session.scalar(stmt)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return PublicUser.model_validate(user)
    finally:
        session.close()


def signout_response(response: Response) -> None:
    """Clear the access_token cookie from the response."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=os.environ.get("APP_ENV", "development") == "production",
        path="/",
    )