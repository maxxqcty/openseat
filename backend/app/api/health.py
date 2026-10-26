"""Health endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


def app_settings(request: Request) -> Settings:
    """Read the settings attached to the current application instance."""
    settings: Settings = request.app.state.settings
    return settings


@router.get("/healthz", response_model=HealthResponse)
def healthz(settings: Annotated[Settings, Depends(app_settings)]) -> HealthResponse:
    """Report process liveness and the deployed version.

    Reports real database connectivity status.
    """
    if not settings.database_url:
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            database="not_configured",
        )

    import psycopg2

    database_status = "unavailable"
    try:
        conn = psycopg2.connect(str(settings.database_url))  # type: ignore
        conn.close()
        database_status = "available"
    except Exception:
        database_status = "unavailable"

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database=database_status,
    )