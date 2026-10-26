"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


@lru_cache(maxsize=8)
def _build_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def get_engine(url: str) -> Engine:
    """Return a pooled engine for the given database URL."""
    return _build_engine(url)


@lru_cache(maxsize=8)
def _build_session_factory(url: str) -> sessionmaker[Session]:
    return sessionmaker(
        bind=_build_engine(url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session_factory(url: str) -> sessionmaker[Session]:
    """Return a session factory for the given database URL."""
    return _build_session_factory(url)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency yielding a database session from application settings."""
    settings: Settings = request.app.state.settings
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    factory = get_session_factory(settings.database_url)
    db = factory()
    try:
        yield db
    finally:
        db.close()
