"""FastAPI application factory."""
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.sessions import router as sessions_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured FastAPI application."""
    resolved = settings or get_settings()

    app = FastAPI(
        title="OpenSeat API",
        version=resolved.app_version,
        description="Booking and waitlist API for small workshops.",
    )
    app.state.settings = resolved
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(sessions_router)
    return app


app = create_app()