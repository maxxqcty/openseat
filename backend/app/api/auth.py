"""Authentication API routes."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import app_settings, get_current_user
from app.config import Settings
from app.db import get_db
from app.errors import ApiError
from app.models.users import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserPublic
from app.services.auth import authenticate_user, create_access_token, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

_RATE_LIMIT = 10
_RATE_WINDOW_SECONDS = 60.0
_attempts: defaultdict[str, list[float]] = defaultdict(list)
_attempts_lock = Lock()


def reset_rate_limits() -> None:
    """Clear the in-memory login throttle. Used by tests."""
    with _attempts_lock:
        _attempts.clear()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(email: str, ip: str) -> None:
    key = f"{email.strip().lower()}|{ip}"
    now = monotonic()
    with _attempts_lock:
        recent = [attempt for attempt in _attempts[key] if now - attempt < _RATE_WINDOW_SECONDS]
        if len(recent) >= _RATE_LIMIT:
            _attempts[key] = recent
            raise ApiError(
                429,
                "rate_limited",
                "Too many login attempts. Try again later.",
            )
        recent.append(now)
        _attempts[key] = recent


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublic,
)
def register(
    payload: RegisterRequest,
    response: Response,
    settings: Annotated[Settings, Depends(app_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Create an account, sign the user in, and return the public profile."""
    user = register_user(
        db,
        display_name=payload.display_name,
        email=str(payload.email),
        password=payload.password,
    )
    _set_session_cookie(response, settings, create_access_token(user.id))
    return user


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(app_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Sign in and set the HttpOnly session cookie."""
    _enforce_rate_limit(str(payload.email), _client_ip(request))
    user = authenticate_user(db, email=str(payload.email), password=payload.password)
    if user is None:
        raise ApiError(401, "unauthorized", "Incorrect email or password")
    _set_session_cookie(response, settings, create_access_token(user.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(
    response: Response,
    settings: Annotated[Settings, Depends(app_settings)],
) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.get("/me", response_model=UserPublic)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return the signed-in user's profile."""
    return user
