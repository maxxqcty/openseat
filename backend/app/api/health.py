"""Health endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.deps import app_settings
from app.config import Settings
from app.db import get_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz(settings: Annotated[Settings, Depends(app_settings)]) -> HealthResponse:
    """Report liveness, version, and real database connectivity."""
    if not settings.database_url:
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            database="not_configured",
        )

    try:
        engine = get_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return HealthResponse(
            status="degraded",
            version=settings.app_version,
            database="unavailable",
        )

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database="available",
    )
