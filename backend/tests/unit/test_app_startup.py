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


def test_database_url_from_render_is_normalized_to_the_sqlalchemy_dialect() -> None:
    # Render's connection string is a libpq URL; SQLAlchemy needs the dialect.
    render_url = "postgres://openseat:secret@dpg-example.render.com:5432/openseat?sslmode=require"
    settings = Settings(
        app_env="development",
        database_url=render_url,
        session_secret="x" * 40,
    )
    assert settings.database_url == (
        "postgresql+psycopg://openseat:secret@dpg-example.render.com:5432/openseat"
        "?sslmode=require"
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


def test_app_version_uses_the_render_commit_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc1234")
    settings = Settings(
        app_env="test",
        app_version="",
        session_secret="x" * 40,
    )
    assert settings.app_version == "abc1234"


def test_cookie_secure_defaults_to_production_but_allows_an_override() -> None:
    production = Settings(app_env="production", session_secret="x" * 40)
    assert production.cookie_secure is True

    local_stack = Settings(
        app_env="production",
        session_secret="x" * 40,
        session_cookie_secure=False,
    )
    assert local_stack.cookie_secure is False
