"""Shared API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.errors import ApiError
from app.models.users import User
from app.services.auth import decode_access_token


def app_settings(request: Request) -> Settings:
    """Read the settings attached to the current application instance."""
    settings: Settings = request.app.state.settings
    return settings


def _user_from_cookie(request: Request, db: Session) -> User | None:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        user_id = decode_access_token(token)
    except ApiError:
        return None
    return db.get(User, user_id)


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Require a signed-in user or raise 401."""
    user = _user_from_cookie(request, db)
    if user is None:
        raise ApiError(401, "unauthorized", "Authentication required")
    return user


def get_optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Return the signed-in user, or None for anonymous requests."""
    return _user_from_cookie(request, db)
