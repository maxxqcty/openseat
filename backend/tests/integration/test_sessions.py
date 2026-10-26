"""Integration tests for sessions against PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session_factory
from app.models.bookings import Booking
from app.models.sessions import Session
from tests.conftest import requires_postgres
from tests.integration.helpers import (
    CSRF_HEADERS,
    book,
    counted_selects,
    create_session,
    login,
    logout,
    register,
)

pytestmark = requires_postgres


def _payload(**overrides: object) -> dict[str, object]:
    starts_at = datetime.now(UTC) + timedelta(hours=24)
    payload: dict[str, object] = {
        "title": "Bookbinding",
        "description": "Make a notebook.",
        "starts_at": starts_at.isoformat(),
        "duration_minutes": 60,
        "capacity": 2,
        "location": "Studio B",
    }
    payload.update(overrides)
    return payload


def test_create_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/sessions", json=_payload(), headers=CSRF_HEADERS)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_create_assigns_caller_as_host(client: TestClient) -> None:
    host = register(client, email="host@example.com", display_name="Host")

    created = create_session(client, capacity=3)

    assert created["host_id"] == host["id"]
    assert created["status"] == "scheduled"
    assert created["capacity"] == 3
    assert created["past"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "ab"},
        {"capacity": 0},
        {"capacity": 101},
        {"duration_minutes": 14},
        {"duration_minutes": 481},
        {"location": "x"},
        {"starts_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()},
    ],
)
def test_create_rejects_invalid_fields(
    client: TestClient,
    overrides: dict[str, object],
) -> None:
    register(client, email="validator@example.com")

    response = client.post(
        "/api/sessions",
        json=_payload(**overrides),
        headers=CSRF_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_is_public_and_orders_by_start(client: TestClient, db_url: str) -> None:
    register(client, email="lister@example.com")
    sooner = create_session(client, starts_in_hours=2, title="Sooner")
    later = create_session(client, starts_in_hours=48, title="Later")
    past = create_session(client, starts_in_hours=1, title="Past")

    with get_session_factory(db_url)() as db:
        target = db.get(Session, uuid.UUID(str(past["id"])))
        assert target is not None
        target.starts_at = datetime.now(UTC) - timedelta(hours=2)
        db.commit()

    client.cookies.clear()
    response = client.get("/api/sessions")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert titles == ["Sooner", "Later"]
    assert sooner["id"] in {item["id"] for item in response.json()}
    assert later["id"] in {item["id"] for item in response.json()}
    assert past["id"] not in {item["id"] for item in response.json()}


def test_detail_returns_counts_and_my_booking(client: TestClient) -> None:
    host = register(client, email="detail-host@example.com")
    created = create_session(client, capacity=2)
    session_id = str(created["id"])

    guest = register(client, email="detail-guest@example.com")
    assert book(client, session_id).status_code == 201

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["confirmed_count"] == 1
    assert detail["checked_in_count"] == 0
    assert detail["waitlist_count"] == 0
    assert detail["my_booking"]["status"] == "confirmed"
    assert str(detail["my_booking"]["user_id"]) == guest["id"]
    assert detail["past"] is False

    client.cookies.clear()
    anonymous = client.get(f"/api/sessions/{session_id}").json()
    assert anonymous["my_booking"] is None
    assert anonymous["confirmed_count"] == 1

    assert host["id"] == detail["host_id"]


def test_detail_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/sessions/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cancel_is_host_only_idempotent_and_cascades(client: TestClient, db_url: str) -> None:
    host = register(client, email="cancel-host@example.com")
    created = create_session(client, capacity=2)
    session_id = str(created["id"])

    guest = register(client, email="cancel-guest@example.com")
    assert book(client, session_id).status_code == 201

    forbidden = client.post(
        f"/api/sessions/{session_id}/cancel",
        headers=CSRF_HEADERS,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"

    login(client, email=host["email"])
    cancelled = client.post(
        f"/api/sessions/{session_id}/cancel",
        headers=CSRF_HEADERS,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["confirmed_count"] == 0
    assert cancelled.json()["waitlist_count"] == 0

    again = client.post(
        f"/api/sessions/{session_id}/cancel",
        headers=CSRF_HEADERS,
    )
    assert again.status_code == 200
    assert again.json()["status"] == "cancelled"

    with get_session_factory(db_url)() as db:
        bookings = db.scalars(
            select(Booking).where(Booking.session_id == uuid.UUID(session_id)),
        ).all()
        assert len(bookings) == 1
        assert bookings[0].status == "cancelled"
        assert bookings[0].cancelled_at is not None
        assert str(bookings[0].user_id) == guest["id"]


def test_list_and_detail_queries_do_not_scale_with_rows(
    client: TestClient,
    db_url: str,
) -> None:
    register(client, email="nplus1-host@example.com")
    for index in range(3):
        create_session(client, starts_in_hours=index + 1, title=f"Session {index}")

    with counted_selects(db_url) as list_statements:
        response = client.get("/api/sessions")
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert len(list_statements) == 1

    created = create_session(client, capacity=1)
    session_id = str(created["id"])

    register(client, email="nplus1-first@example.com")
    assert book(client, session_id).json()["status"] == "confirmed"
    register(client, email="nplus1-waiter@example.com")
    assert book(client, session_id).json()["status"] == "waitlisted"

    with counted_selects(db_url) as first_detail:
        detail = client.get(f"/api/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["my_booking"]["waitlist_position"] == 1

    register(client, email="nplus1-second-waiter@example.com")
    assert book(client, session_id).json()["status"] == "waitlisted"

    with counted_selects(db_url) as second_detail:
        detail = client.get(f"/api/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["my_booking"]["waitlist_position"] == 2
    assert len(second_detail) == len(first_detail)
    # auth lookup, session, counts, my booking, waitlist position.
    assert len(first_detail) == 5


def test_cancel_unknown_session_returns_404(client: TestClient) -> None:
    register(client, email="cancel-404@example.com")

    response = client.post(
        f"/api/sessions/{uuid.uuid4()}/cancel",
        headers=CSRF_HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cancelled_session_cannot_be_booked(client: TestClient) -> None:
    host = register(client, email="closed-host@example.com")
    created = create_session(client, capacity=1)
    session_id = str(created["id"])

    client.post(f"/api/sessions/{session_id}/cancel", headers=CSRF_HEADERS)
    logout(client)
    login(client, email=host["email"])
    client.post(f"/api/sessions/{session_id}/cancel", headers=CSRF_HEADERS)

    register(client, email="too-late@example.com")
    response = book(client, session_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
