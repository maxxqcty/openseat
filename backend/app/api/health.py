"""Health endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import app_settings
from app.config import Settings
from app.db import get_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unavailable."}},
)
def healthz(settings: Annotated[Settings, Depends(app_settings)]) -> HealthResponse | JSONResponse:
    """Report liveness, version, and real database connectivity.

    A database failure returns 503 so platform health checks (Render, Docker
    ``curl -f``) see the outage instead of a 200 with a "degraded" body.
    """
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
        degraded = HealthResponse(
            status="degraded",
            version=settings.app_version,
            database="unavailable",
        )
        return JSONResponse(status_code=503, content=degraded.model_dump())

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database="available",
    )
