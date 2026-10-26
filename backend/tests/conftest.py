"""Shared pytest configuration for OpenSeat backend tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

# Must be set before any app module is imported: settings are cached.
os.environ["APP_ENV"] = "test"
os.environ.setdefault(
    "SESSION_SECRET",
    "test-secret-0123456789abcdef0123456789abcdef",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.api.auth import reset_rate_limits  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://openseat:openseat@localhost:55432/openseat_test"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def _database_available(url: str) -> bool:
    try:
        # Bound the probe: without a timeout, libpq can wait indefinitely for a
        # refused port and hang every pytest run at import time.
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except Exception:
        return False
    return True


DATABASE_AVAILABLE = _database_available(TEST_DATABASE_URL)

TABLES = ("bookings", "sessions", "users")


def reset_database(database_url: str) -> None:
    """Delete every application row so each test starts from a clean slate."""
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {', '.join(TABLES)} CASCADE"),
        )
    engine.dispose()


requires_postgres = pytest.mark.skipif(
    not DATABASE_AVAILABLE,
    reason="PostgreSQL test database is not available",
)


@pytest.fixture(autouse=True)
def _clean_rate_limits() -> Iterator[None]:
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Apply migrations to a clean PostgreSQL schema once per session."""
    if not DATABASE_AVAILABLE:
        pytest.skip("PostgreSQL test database is not available")

    from alembic import command
    from alembic.config import Config

    engine = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture()
def db_url(database_url: str) -> str:
    """Truncate all tables before each integration test."""
    reset_database(database_url)
    return database_url


@pytest.fixture()
def settings(db_url: str) -> Settings:
    return Settings(
        app_env="test",
        app_version="test-version",
        database_url=db_url,
        session_secret="x" * 40,
    )


@pytest.fixture()
def app(settings: Settings) -> object:
    return create_app(settings)


@pytest.fixture()
def client(app: object) -> Iterator[TestClient]:
    with TestClient(app) as test_client:  # type: ignore[arg-type]
        yield test_client
