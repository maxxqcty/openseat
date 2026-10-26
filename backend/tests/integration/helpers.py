"""Helpers shared by integration tests."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import get_engine

CSRF_HEADERS = {"X-Requested-With": "openseat"}
PASSWORD = "password123"


def register(
    client: TestClient,
    *,
    email: str,
    display_name: str = "Guest",
    password: str = PASSWORD,
) -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": display_name,
            "email": email,
            "password": password,
        },
        headers=CSRF_HEADERS,
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(
    client: TestClient,
    *,
    email: str,
    password: str = PASSWORD,
) -> object:
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=CSRF_HEADERS,
    )


def logout(client: TestClient) -> None:
    response = client.post("/api/auth/logout", headers=CSRF_HEADERS)
    assert response.status_code == 204, response.text


def create_session(
    client: TestClient,
    *,
    capacity: int = 2,
    starts_in_hours: float = 24,
    duration_minutes: int = 60,
    title: str = "Risograph Basics",
) -> dict[str, object]:
    starts_at = datetime.now(UTC) + timedelta(hours=starts_in_hours)
    response = client.post(
        "/api/sessions",
        json={
            "title": title,
            "description": "Bring a shirt.",
            "starts_at": starts_at.isoformat(),
            "duration_minutes": duration_minutes,
            "capacity": capacity,
            "location": "Studio A",
        },
        headers=CSRF_HEADERS,
    )
    assert response.status_code == 201, response.text
    return response.json()


def book(client: TestClient, session_id: str) -> object:
    return client.post(
        f"/api/sessions/{session_id}/bookings",
        headers=CSRF_HEADERS,
    )


@contextmanager
def counted_selects(url: str) -> Iterator[list[str]]:
    """Record SELECT statements executed on the shared engine."""
    engine = get_engine(url)
    statements: list[str] = []

    def record(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def session_id(value: dict[str, object]) -> uuid.UUID:
    return uuid.UUID(str(value["id"]))
