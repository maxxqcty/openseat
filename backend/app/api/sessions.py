"""Session API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException

from app.config import get_settings, get_db_session
from app.services.sessions import (
    create_session,
    list_sessions,
    get_session,
    cancel_session,
    STATUS_CHOICES,
)
from app.api.auth import get_current_user, signout_response
from app.schemas.sessions import SessionPublic

router = APIRouter(prefix="/api/sessions", tags=["sessions"])