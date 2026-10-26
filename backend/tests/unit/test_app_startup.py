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


def test_database_url_from_fly_is_normalized_to_the_sqlalchemy_dialect() -> None:
    # `fly mpg attach` writes a libpq URL; SQLAlchemy needs the dialect.
    fly_url = "postgres://openseat:secret@host.flycast:5432/openseat?sslmode=require"
    settings = Settings(
        app_env="development",
        database_url=fly_url,
        session_secret="x" * 40,
    )
    assert settings.database_url == (
        "postgresql+psycopg://openseat:secret@host.flycast:5432/openseat?sslmode=require"
    )


def test_an_already_explicit_database_url_is_left_alone() -> None:
    url = "postgresql+psycopg://openseat:openseat@localhost:55432/openseat_test"
    settings = Settings(
        app_env="test",
        database_url=url,
        session_secret="x" * 40,
    )
    assert settings.database_url == url

    missing = Settings(app_env="test", database_url=None, session_secret="x" * 40)
    assert missing.database_url is None
