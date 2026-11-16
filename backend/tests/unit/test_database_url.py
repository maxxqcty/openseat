"""Hosted-provider database URLs must resolve to the psycopg v3 driver."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import normalize_database_url

DRIVER_URL = "postgresql+psycopg://user:pw@host:5432/db"


@pytest.mark.parametrize(
    "raw",
    [
        "postgres://user:pw@host:5432/db",
        "postgresql://user:pw@host:5432/db",
    ],
)
def test_libpq_urls_get_the_psycopg_driver(raw: str) -> None:
    assert normalize_database_url(raw) == DRIVER_URL


def test_explicit_driver_and_none_are_left_alone() -> None:
    assert normalize_database_url(DRIVER_URL) == DRIVER_URL
    assert normalize_database_url(None) is None


def test_alembic_env_normalizes_the_url() -> None:
    """Regression: Render deploy failed with ``No module named 'psycopg2'``.

    Alembic reads ``DATABASE_URL`` itself, so it must apply the same
    normalization as the app instead of using the raw ``postgres://`` value.
    """
    env_py = Path(__file__).parents[2] / "migrations" / "env.py"
    source = env_py.read_text(encoding="utf-8")
    assert "normalize_database_url" in source
