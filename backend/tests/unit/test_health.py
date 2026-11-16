"""Unit tests for the health endpoint."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(
        Settings(
            app_env="test",
            app_version="test-version",
            database_url=None,
            session_secret="x" * 40,
        ),
    )
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_reports_status_version_and_database(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "status": "ok",
        "version": "test-version",
        "database": "not_configured",
    }


def test_healthz_rejects_unsupported_method(client: TestClient) -> None:
    response = client.post("/healthz")

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


def test_healthz_returns_503_when_the_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_engine(url: str) -> object:
        raise RuntimeError("database down")

    monkeypatch.setattr("app.api.health.get_engine", broken_engine)
    app = create_app(
        Settings(
            app_env="test",
            app_version="test-version",
            database_url="postgresql+psycopg://x:x@localhost/none",
            session_secret="x" * 40,
        ),
    )
    with TestClient(app) as test_client:
        response = test_client.get("/healthz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "version": "test-version",
        "database": "unavailable",
    }
