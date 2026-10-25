"""Health endpoint."""

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
    """Report process liveness and the deployed version."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database="not_configured",
    )
