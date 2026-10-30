"""Unit tests for the JSON error envelope on framework errors."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client() -> TestClient:
    settings = Settings(
        app_env="test",
        database_url=None,
        session_secret="x" * 40,
    )
    return TestClient(create_app(settings))


def test_unknown_api_route_returns_the_error_envelope() -> None:
    with _client() as client:
        response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Not found",
            "details": {},
        }
    }


def test_bare_api_path_returns_json_not_the_spa() -> None:
    with _client() as client:
        response = client.get("/api")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "not_found"


def test_api_method_not_allowed_returns_the_error_envelope() -> None:
    with _client() as client:
        response = client.get("/api/auth/logout")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_non_api_404_keeps_the_framework_shape() -> None:
    with _client() as client:
        response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
