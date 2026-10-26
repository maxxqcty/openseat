"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.auth import router as auth_router
from app.api.bookings import router as bookings_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.config import Settings, get_settings
from app.db import get_engine
from app.errors import error_body, install_error_handlers

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CSRF_HEADER = "X-Requested-With"
_CSRF_VALUE = "openseat"


def _check_database(settings: Settings) -> None:
    if settings.app_env == "test":
        return
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    try:
        engine = get_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(f"Database is unreachable: {exc}") from exc


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured FastAPI application."""
    resolved = settings or get_settings()
    _check_database(resolved)

    app = FastAPI(
        title="OpenSeat API",
        version=resolved.app_version,
        description="Booking and waitlist API for small workshops.",
    )
    app.state.settings = resolved
    install_error_handlers(app)

    @app.middleware("http")
    async def csrf_guard(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if (
            request.method in _MUTATING_METHODS
            and request.url.path.startswith("/api/")
            and request.headers.get(_CSRF_HEADER) != _CSRF_VALUE
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content=error_body(
                    "forbidden",
                    "Missing or invalid X-Requested-With header",
                ),
            )
        return await call_next(request)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(bookings_router)
    return app


app = create_app()
