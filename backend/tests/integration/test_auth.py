"""Integration tests for authentication against PostgreSQL."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import requires_postgres
from tests.integration.helpers import CSRF_HEADERS, PASSWORD, login, logout, register

pytestmark = requires_postgres


def test_register_returns_only_public_fields(client: TestClient) -> None:
    body = register(client, email="alice@example.com", display_name="Alice")

    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice"
    assert set(body) == {"id", "email", "display_name", "created_at"}
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_is_case_insensitive(client: TestClient) -> None:
    register(client, email="Case@Example.com")

    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Other",
            "email": "case@example.com",
            "password": PASSWORD,
        },
        headers=CSRF_HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (
            {"display_name": "A", "email": "not-an-email", "password": PASSWORD},
            "invalid email",
        ),
        (
            {"display_name": "A", "email": "short@example.com", "password": "short"},
            "short password",
        ),
        (
            {"display_name": "   ", "email": "blank@example.com", "password": PASSWORD},
            "blank display name",
        ),
    ],
)
def test_register_validation_returns_422(
    client: TestClient,
    payload: dict[str, str],
    reason: str,
) -> None:
    response = client.post(
        "/api/auth/register",
        json=payload,
        headers=CSRF_HEADERS,
    )

    assert response.status_code == 422, reason
    assert response.json()["error"]["code"] == "validation_error"


def test_login_sets_httponly_lax_cookie(client: TestClient) -> None:
    register(client, email="login@example.com", display_name="Login User")
    logout(client)

    response = login(client, email="login@example.com")

    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "secure" not in cookie
    assert "openseat_session=" in cookie


def test_secure_cookie_in_production(db_url: str) -> None:
    app = create_app(
        Settings(
            app_env="production",
            app_version="test-version",
            database_url=db_url,
            session_secret="z" * 40,
        ),
    )
    with TestClient(app) as production_client:
        register(production_client, email="prod@example.com")
        logout(production_client)

        response = login(production_client, email="prod@example.com")

    assert response.status_code == 204
    assert "secure" in response.headers["set-cookie"].lower()


def test_wrong_password_returns_401_error_shape(client: TestClient) -> None:
    register(client, email="wrong@example.com")
    logout(client)

    response = login(client, email="wrong@example.com", password="not-the-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_is_rate_limited_after_ten_attempts(client: TestClient) -> None:
    register(client, email="limit@example.com")
    logout(client)

    for _ in range(10):
        response = login(client, email="limit@example.com", password="bad-password")
        assert response.status_code == 401

    blocked = login(client, email="limit@example.com", password="bad-password")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"


def test_logout_clears_the_session(client: TestClient) -> None:
    register(client, email="bye@example.com")

    assert client.get("/api/auth/me").status_code == 200
    logout(client)

    assert client.get("/api/auth/me").status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_mutating_requests_require_csrf_header(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "No CSRF",
            "email": "csrf@example.com",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_health_reports_available_database(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "test-version",
        "database": "available",
    }
