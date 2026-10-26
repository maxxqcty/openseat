"""Integration tests for the host roster and check-in API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.db import get_session_factory
from app.models.bookings import Booking
from app.models.sessions import Session
from app.services import roster as roster_service
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


def _host_and_session(
    client: TestClient,
    *,
    capacity: int = 2,
    starts_in_hours: float = 1,
) -> dict[str, Any]:
    register(client, email="host@example.com", display_name="Host")
    return create_session(client, capacity=capacity, starts_in_hours=starts_in_hours)


def _guest_books(
    client: TestClient,
    session_id: str,
    *,
    email: str,
    display_name: str,
) -> dict[str, Any]:
    register(client, email=email, display_name=display_name)
    response = book(client, session_id)
    assert response.status_code == 201, response.text
    return response.json()


def test_roster_groups_and_orders_entries(client: TestClient, db_url: str) -> None:
    created = _host_and_session(client, capacity=4)
    session_id = str(created["id"])

    guests = {}
    for email, name in (
        ("alice@example.com", "Alice"),
        ("bob@example.com", "Bob"),
        ("erin@example.com", "Erin"),
        ("frank@example.com", "Frank"),
    ):
        body = _guest_books(client, session_id, email=email, display_name=name)
        assert body["status"] == "confirmed"
        guests[name] = body

    carol = _guest_books(
        client,
        session_id,
        email="carol@example.com",
        display_name="Carol",
    )
    dave = _guest_books(client, session_id, email="dave@example.com", display_name="Dave")
    assert carol["waitlist_position"] == 1
    assert dave["waitlist_position"] == 2

    earlier = datetime.now(UTC) - timedelta(minutes=2)
    later = datetime.now(UTC) - timedelta(minutes=1)
    with get_session_factory(db_url)() as db:
        for name, checked_in_at in (("Alice", earlier), ("Bob", later)):
            booking = db.get(Booking, uuid.UUID(str(guests[name]["id"])))
            assert booking is not None
            booking.status = "checked_in"
            booking.checked_in_at = checked_in_at
        db.commit()

    login(client, email="host@example.com")
    with counted_selects(db_url) as statements:
        response = client.get(f"/api/sessions/{session_id}/bookings")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"confirmed", "waitlisted", "checked_in"}
    assert [entry["display_name"] for entry in body["checked_in"]] == ["Alice", "Bob"]
    assert [entry["display_name"] for entry in body["confirmed"]] == ["Erin", "Frank"]
    assert [entry["display_name"] for entry in body["waitlisted"]] == ["Carol", "Dave"]
    assert [entry["waitlist_position"] for entry in body["waitlisted"]] == [1, 2]
    assert all(entry["waitlist_position"] is None for entry in body["confirmed"])

    entry_fields = {
        "booking_id",
        "display_name",
        "status",
        "created_at",
        "checked_in_at",
        "waitlist_position",
    }
    assert all(set(entry) == entry_fields for entry in body["confirmed"])
    assert body["checked_in"][0]["checked_in_at"] is not None
    assert body["confirmed"][0]["checked_in_at"] is None
    assert "@example.com" not in response.text
    # auth lookup, session, bookings with names, and batched positions.
    assert len(statements) == 4

    login(client, email="dave@example.com")
    assert client.delete(f"/api/bookings/{dave['id']}", headers=CSRF_HEADERS).status_code == 204
    login(client, email="host@example.com")
    after_cancel = client.get(f"/api/sessions/{session_id}/bookings").json()
    assert [entry["display_name"] for entry in after_cancel["waitlisted"]] == ["Carol"]
    assert after_cancel["waitlisted"][0]["waitlist_position"] == 1


def test_roster_is_host_only_and_hides_unknown_sessions(client: TestClient) -> None:
    created = _host_and_session(client, capacity=1)
    session_id = str(created["id"])
    _guest_books(client, session_id, email="alice@example.com", display_name="Alice")

    login(client, email="alice@example.com")
    forbidden = client.get(f"/api/sessions/{session_id}/bookings")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"

    logout(client)
    unauthenticated = client.get(f"/api/sessions/{session_id}/bookings")
    assert unauthenticated.status_code == 401

    login(client, email="host@example.com")
    unknown = client.get(f"/api/sessions/{uuid.uuid4()}/bookings")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"


def test_host_checks_in_confirmed_guest_and_seat_stays_taken(client: TestClient) -> None:
    created = _host_and_session(client, capacity=1)
    session_id = str(created["id"])
    alice = _guest_books(client, session_id, email="alice@example.com", display_name="Alice")
    bob = _guest_books(client, session_id, email="bob@example.com", display_name="Bob")
    assert bob["status"] == "waitlisted"

    login(client, email="host@example.com")
    response = client.post(f"/api/bookings/{alice['id']}/check-in", headers=CSRF_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "checked_in"
    assert body["checked_in_at"] is not None
    checked_in_at = body["checked_in_at"]

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["checked_in_count"] == 1
    assert detail["confirmed_count"] == 0
    assert detail["waitlist_count"] == 1

    roster = client.get(f"/api/sessions/{session_id}/bookings").json()
    assert [entry["display_name"] for entry in roster["checked_in"]] == ["Alice"]

    again = client.post(f"/api/bookings/{alice['id']}/check-in", headers=CSRF_HEADERS)
    assert again.status_code == 200
    assert again.json()["status"] == "checked_in"
    assert again.json()["checked_in_at"] == checked_in_at

    register(client, email="erin@example.com", display_name="Erin")
    still_full = book(client, session_id)
    assert still_full.status_code == 201
    assert still_full.json()["status"] == "waitlisted"
    assert still_full.json()["waitlist_position"] == 2


def test_check_in_window_boundaries(
    client: TestClient,
    db_url: str,
    monkeypatch: MonkeyPatch,
) -> None:
    frozen = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(roster_service, "utc_now", lambda: frozen)

    register(client, email="host@example.com", display_name="Host")
    register(client, email="guest@example.com", display_name="Guest")

    cases = (
        ("opens", frozen + timedelta(hours=2), 200),
        ("too-early", frozen + timedelta(hours=2, seconds=1), 409),
        ("inside", frozen + timedelta(minutes=30), 200),
        ("closes", frozen - timedelta(minutes=60), 200),
        ("ended", frozen - timedelta(minutes=61), 409),
    )
    for name, starts_at, expected in cases:
        login(client, email="host@example.com")
        created = create_session(client, capacity=1, title=name)
        login(client, email="guest@example.com")
        booking = book(client, str(created["id"])).json()
        assert booking["status"] == "confirmed"

        with get_session_factory(db_url)() as db:
            session = db.get(Session, uuid.UUID(str(created["id"])))
            assert session is not None
            session.starts_at = starts_at
            db.commit()

        login(client, email="host@example.com")
        response = client.post(
            f"/api/bookings/{booking['id']}/check-in",
            headers=CSRF_HEADERS,
        )
        assert response.status_code == expected, name


def test_check_in_rejects_waitlisted_and_cancelled_bookings(client: TestClient) -> None:
    created = _host_and_session(client, capacity=1)
    session_id = str(created["id"])
    alice = _guest_books(client, session_id, email="alice@example.com", display_name="Alice")
    bob = _guest_books(client, session_id, email="bob@example.com", display_name="Bob")

    login(client, email="host@example.com")
    waitlisted = client.post(f"/api/bookings/{bob['id']}/check-in", headers=CSRF_HEADERS)
    assert waitlisted.status_code == 409
    assert waitlisted.json()["error"]["code"] == "conflict"

    login(client, email="alice@example.com")
    assert client.delete(f"/api/bookings/{alice['id']}", headers=CSRF_HEADERS).status_code == 204

    login(client, email="host@example.com")
    cancelled = client.post(f"/api/bookings/{alice['id']}/check-in", headers=CSRF_HEADERS)
    assert cancelled.status_code == 409
    assert cancelled.json()["error"]["code"] == "conflict"


def test_check_in_is_host_only_and_hides_unknown_bookings(client: TestClient) -> None:
    created = _host_and_session(client, capacity=1)
    session_id = str(created["id"])
    alice = _guest_books(client, session_id, email="alice@example.com", display_name="Alice")
    _guest_books(client, session_id, email="bob@example.com", display_name="Bob")

    login(client, email="bob@example.com")
    forbidden = client.post(f"/api/bookings/{alice['id']}/check-in", headers=CSRF_HEADERS)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"

    login(client, email="host@example.com")
    unknown = client.post(
        f"/api/bookings/{uuid.uuid4()}/check-in",
        headers=CSRF_HEADERS,
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"

    logout(client)
    unauthenticated = client.post(
        f"/api/bookings/{alice['id']}/check-in",
        headers=CSRF_HEADERS,
    )
    assert unauthenticated.status_code == 401
