"""Unit tests for fail-fast startup checks."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.main import create_app


def test_startup_fails_without_database_url() -> None:
    settings = Settings(
        app_env="development",
        database_url=None,
        session_secret="x" * 40,
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app(settings)
